#!/usr/bin/env bash
# shellcheck disable=SC2154 source=/dev/null

################################################################################
# GPU discovery and optional CUDA toolkit installation.
#
# This script never installs or replaces an NVIDIA display driver. CUDA is added
# from NVIDIA's signed network repository and only after an explicit opt-in.
################################################################################

source "$(dirname "${BASH_SOURCE[0]}")/shared-utils.sh"

CUDA_ROOT=""
nvidia_arch_type=""
gpu_flag=1
has_vulkan_gpu=0
is_nvidia_gpu_present="NVIDIA GPU not detected"
is_amd_gpu_present="AMD GPU not detected"
is_intel_gpu_present="Intel GPU not detected"

_gpu_controller_lines() {
    command -v lspci >/dev/null 2>&1 || return 0
    lspci -nn 2>/dev/null |
        grep -iE 'vga compatible controller|3d controller|display controller' || true
}

detect_gpu_vendors() {
    local controllers nvidia_smi_path

    gpu_flag=1
    has_vulkan_gpu=0
    is_nvidia_gpu_present="NVIDIA GPU not detected"
    is_amd_gpu_present="AMD GPU not detected"
    is_intel_gpu_present="Intel GPU not detected"

    controllers="$(_gpu_controller_lines)"
    nvidia_smi_path="$(command -v nvidia-smi 2>/dev/null || true)"
    if [[ -z "$nvidia_smi_path" && -x /usr/lib/wsl/lib/nvidia-smi ]]; then
        nvidia_smi_path=/usr/lib/wsl/lib/nvidia-smi
        path_prepend /usr/lib/wsl/lib
    fi

    if [[ -n "$nvidia_smi_path" ]] &&
        "$nvidia_smi_path" --query-gpu=name --format=csv,noheader >/dev/null 2>&1; then
        is_nvidia_gpu_present="NVIDIA GPU detected"
    elif grep -qi nvidia <<<"$controllers"; then
        is_nvidia_gpu_present="NVIDIA GPU detected"
    fi

    if grep -qiE 'amd/ati|advanced micro devices|radeon' <<<"$controllers"; then
        is_amd_gpu_present="AMD GPU detected"
    fi
    if grep -qi intel <<<"$controllers"; then
        is_intel_gpu_present="Intel GPU detected"
    fi

    if [[ "$is_nvidia_gpu_present" == "NVIDIA GPU detected" ]]; then
        gpu_flag=0
    fi
    if [[ "$is_nvidia_gpu_present" == "NVIDIA GPU detected" ||
        "$is_amd_gpu_present" == "AMD GPU detected" ||
        "$is_intel_gpu_present" == "Intel GPU detected" ]]; then
        has_vulkan_gpu=1
    fi

    # Compatibility aliases used by a few build recipes.
    amd_gpu_test="$is_amd_gpu_present"
    export is_nvidia_gpu_present is_amd_gpu_present is_intel_gpu_present
    export amd_gpu_test gpu_flag has_vulkan_gpu
}

find_cuda_root() {
    local nvcc_path candidate

    nvcc_path="$(command -v nvcc 2>/dev/null || true)"
    if [[ -n "$nvcc_path" ]]; then
        nvcc_path="$(readlink -f -- "$nvcc_path" 2>/dev/null || printf '%s' "$nvcc_path")"
        candidate="$(dirname -- "$(dirname -- "$nvcc_path")")"
        if [[ -x "$candidate/bin/nvcc" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    fi

    for candidate in /usr/local/cuda /opt/cuda; do
        if [[ -x "$candidate/bin/nvcc" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

get_local_cuda_version() {
    local cuda_root="${1:-${CUDA_ROOT:-}}"
    local version

    [[ -n "$cuda_root" && -x "$cuda_root/bin/nvcc" ]] || return 1
    version="$(
        "$cuda_root/bin/nvcc" --version 2>/dev/null |
            sed -nE 's/.*release ([0-9]+(\.[0-9]+){1,2}).*/\1/p' |
            sed -n '1p'
    )"
    [[ "$version" =~ ^[0-9]+(\.[0-9]+){1,2}$ ]] || return 1
    printf '%s\n' "$version"
}

cuda_repository_name() {
    if [[ "${VARIABLE_OS:-}" == "WSL2" ]]; then
        printf 'wsl-ubuntu\n'
        return 0
    fi

    case "${OS:-}:${VER:-}" in
        Ubuntu:22.04) printf 'ubuntu2204\n' ;;
        Ubuntu:24.04) printf 'ubuntu2404\n' ;;
        Ubuntu:26.04) printf 'ubuntu2604\n' ;;
        Debian:12) printf 'debian12\n' ;;
        Debian:13) printf 'debian13\n' ;;
        *) return 1 ;;
    esac
}

install_cuda_toolkit() {
    local repository keyring_url temp_directory keyring_file

    repository="$(cuda_repository_name)" ||
        fail "No supported NVIDIA CUDA repository mapping exists for '$OS $VER'."
    temp_directory="$(mktemp -d)" ||
        fail "Unable to create a temporary CUDA setup directory."
    keyring_file="$temp_directory/cuda-keyring.deb"
    keyring_url="https://developer.download.nvidia.com/compute/cuda/repos"
    keyring_url+="/$repository/x86_64/cuda-keyring_1.1-1_all.deb"

    log "Downloading NVIDIA's CUDA repository keyring for '$repository'..."
    if ! curl_https --fail --silent --show-error --location \
        --retry 3 --retry-all-errors --connect-timeout "${DOWNLOAD_CONNECT_TIMEOUT:-5}" \
        --max-time 120 --output "$keyring_file" "$keyring_url"; then
        safe_remove_tree "$temp_directory" "$(dirname -- "$temp_directory")"
        fail "Unable to download NVIDIA's CUDA repository keyring."
    fi

    execute sudo dpkg -i "$keyring_file"
    safe_remove_tree "$temp_directory" "$(dirname -- "$temp_directory")"
    # This state is owned by the previously sourced system-setup.sh.
    # shellcheck disable=SC2034
    APT_INDEX_UPDATED=false
    apt_update_once
    execute sudo env DEBIAN_FRONTEND=noninteractive \
        apt "${APT_SCRIPT_OPTIONS[@]}" install --assume-yes \
        --no-install-recommends cuda-toolkit
    hash -r
    source_path
}

read_cuda_architectures() {
    local nvcc="${CUDA_ROOT}/bin/nvcc"
    local architecture

    CUDA_AVAILABLE_ARCHITECTURES=()
    while IFS= read -r architecture; do
        [[ "$architecture" =~ ^[0-9]+$ ]] || continue
        CUDA_AVAILABLE_ARCHITECTURES+=("$architecture")
    done < <(
        "$nvcc" --list-gpu-code 2>/dev/null |
            grep -oE 'sm_[0-9]+' |
            sed 's/^sm_//' |
            sort -nu
    )
    ((${#CUDA_AVAILABLE_ARCHITECTURES[@]} > 0))
}

read_installed_gpu_architectures() {
    local capability architecture
    local -A seen_architectures=()

    CUDA_INSTALLED_GPU_ARCHITECTURES=()
    command -v nvidia-smi >/dev/null 2>&1 || return 1
    while IFS= read -r capability; do
        capability="$(trim_whitespace "$capability")"
        [[ "$capability" =~ ^[0-9]+\.[0-9]+$ ]] || continue
        architecture="${capability/.}"
        if [[ -z "${seen_architectures[$architecture]+x}" ]]; then
            seen_architectures["$architecture"]=1
            CUDA_INSTALLED_GPU_ARCHITECTURES+=("$architecture")
        fi
    done < <(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null)
    ((${#CUDA_INSTALLED_GPU_ARCHITECTURES[@]} > 0))
}

architecture_is_supported() {
    local requested="${1:-}" available

    for available in "${CUDA_AVAILABLE_ARCHITECTURES[@]}"; do
        [[ "$available" == "$requested" ]] && return 0
    done
    return 1
}

nvidia_architecture() {
    local mode="${CUDA_ARCH_MODE:-native}"
    local custom="${CUDA_ARCHITECTURES:-}"
    local architecture highest=""
    local -a selected=()
    local -a custom_values=()
    local -a flags=()
    local -A selected_seen=()

    [[ -n "$CUDA_ROOT" ]] || CUDA_ROOT="$(find_cuda_root)" || return 1
    read_cuda_architectures ||
        fail "'nvcc' did not report any supported GPU code targets."

    case "$mode" in
        native)
            read_installed_gpu_architectures || {
                warn "'nvidia-smi' could not report GPU compute capabilities."
                return 1
            }
            selected=("${CUDA_INSTALLED_GPU_ARCHITECTURES[@]}")
            ;;
        all)
            selected=("${CUDA_AVAILABLE_ARCHITECTURES[@]}")
            ;;
        custom)
            custom="${custom//,/ }"
            read -r -a custom_values <<<"$custom"
            ((${#custom_values[@]} > 0)) ||
                fail "'CUDA_ARCH_MODE=custom' requires 'CUDA_ARCHITECTURES' (for example: '86 89')."
            selected=("${custom_values[@]}")
            ;;
        *)
            fail "Invalid 'CUDA_ARCH_MODE' value '$mode'; expected 'native', 'all', or 'custom'."
            ;;
    esac

    for architecture in "${selected[@]}"; do
        [[ "$architecture" =~ ^[0-9]+$ ]] ||
            fail "Invalid CUDA architecture '$architecture'."
        [[ -z "${selected_seen[$architecture]+x}" ]] || continue
        selected_seen["$architecture"]=1
        if ! architecture_is_supported "$architecture"; then
            if [[ "$mode" == "native" ]]; then
                warn "CUDA toolkit does not support this GPU's 'sm_$architecture' target (available: '${CUDA_AVAILABLE_ARCHITECTURES[*]}')."
                return 1
            fi
            fail "CUDA toolkit does not support 'sm_$architecture' (available: '${CUDA_AVAILABLE_ARCHITECTURES[*]}')."
        fi
        flags+=("-gencode arch=compute_${architecture},code=sm_${architecture}")
        if [[ -z "$highest" || "$architecture" -gt "$highest" ]]; then
            highest="$architecture"
        fi
    done
    [[ -n "$highest" ]] || return 1
    flags+=("-gencode arch=compute_${highest},code=compute_${highest}")

    nvidia_arch_type="${flags[*]}"
    export CUDA_ROOT nvidia_arch_type
    log "CUDA targets: '${selected[*]}' (PTX fallback: 'compute_$highest')."
}

configure_nvidia_architecture_once() {
    local failure_context="${1:-CUDA configuration}"

    [[ -n "$nvidia_arch_type" ]] && return 0
    if ! nvidia_architecture; then
        warn "$failure_context: CUDA architecture detection failed; CUDA compilation will be disabled."
        return 1
    fi
}

install_cuda() {
    local install_mode="${CUDA_INSTALL:-ask}"
    local answer local_version

    case "$install_mode" in
        ask|always|never) ;;
        *) fail "Invalid 'CUDA_INSTALL' value '$install_mode'; expected 'ask', 'always', or 'never'." ;;
    esac
    [[ "$is_nvidia_gpu_present" == "NVIDIA GPU detected" ]] || return 0

    CUDA_ROOT="$(find_cuda_root || true)"
    if [[ -n "$CUDA_ROOT" ]]; then
        local_version="$(get_local_cuda_version "$CUDA_ROOT" || true)"
        log "CUDA toolkit detected at '$CUDA_ROOT' (version '${local_version:-unknown}')."
        configure_nvidia_architecture_once "Installed CUDA toolkit"
        export CUDA_ROOT
        return 0
    fi

    if [[ "$install_mode" == "never" ]]; then
        warn "NVIDIA GPU detected, but 'CUDA_INSTALL=never' and no toolkit is installed."
        return 0
    fi
    if [[ "$install_mode" == "ask" ]]; then
        if [[ ! -t 0 ]]; then
            warn "NVIDIA GPU detected, but input is non-interactive; skipping CUDA toolkit installation."
            return 0
        fi
        printf '\n'
        read -r -p "Install the CUDA toolkit from NVIDIA's signed APT repository? [y/N]: " answer
        [[ "$answer" =~ ^([yY]|[yY][eE][sS])$ ]] || return 0
    fi

    install_cuda_toolkit
    CUDA_ROOT="$(find_cuda_root || true)"
    [[ -n "$CUDA_ROOT" ]] ||
        fail "CUDA toolkit installation completed, but 'nvcc' could not be located."
    configure_nvidia_architecture_once "New CUDA toolkit"
    export CUDA_ROOT
}

initialize_hardware_detection() {
    detect_gpu_vendors

    printf '\n'
    box_out_banner "Hardware Detection"
    printf 'NVIDIA: %s\n' "$is_nvidia_gpu_present"
    printf 'AMD:    %s\n' "$is_amd_gpu_present"
    printf 'Intel:  %s\n' "$is_intel_gpu_present"
    if ((has_vulkan_gpu == 0)); then
        warn "No supported GPU was detected; proprietary GPU integrations will be omitted and generic hardware APIs may have no runtime device."
    fi
}
