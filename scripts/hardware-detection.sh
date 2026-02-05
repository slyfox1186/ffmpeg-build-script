#!/usr/bin/env bash
# shellcheck disable=SC2068,SC2154,SC2162,SC2317 source=/dev/null

####################################################################################
##
##  FFmpeg Build Script - Hardware Detection
##  GPU/CPU detection, CUDA installation, and hardware acceleration functions
##
####################################################################################

# Source shared utilities
source "$(dirname "${BASH_SOURCE[0]}")/shared-utils.sh"

# Global variables
remote_cuda_version=""
DEFAULT_CUDA_VERSION="12.8.1"

# AMD GPU detection
check_amd_gpu() {
    if command -v lshw >/dev/null 2>&1 && lshw -C display 2>&1 | grep -Eioq "amdgpu|amd"; then
        echo "AMD GPU detected"
    elif dpkg -l 2>&1 | grep -iq "amdgpu"; then
        echo "AMD GPU detected"
    elif command -v lspci >/dev/null 2>&1 && lspci 2>&1 | grep -iq "amd"; then
        echo "AMD GPU detected"
    else
        echo "No AMD GPU detected"
    fi
}

# NVIDIA GPU detection (works in both native Linux and WSL2)
check_nvidia_gpu() {
    local found=0
    local gpu_info=""

    # Primary detection: nvidia-smi (most reliable)
    if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi --query-gpu=name --format=csv,noheader &>/dev/null; then
        is_nvidia_gpu_present="NVIDIA GPU detected"
        return 0
    fi

    # Fallback: lspci (capture output to variable first to avoid pipe issues)
    if ! grep -Eiq '(microsoft|slyfox1186)' /proc/version; then
        if command -v lspci >/dev/null 2>&1; then
            local lspci_output
            lspci_output=$(lspci 2>/dev/null)
            if echo "$lspci_output" | grep -qi nvidia; then
                is_nvidia_gpu_present="NVIDIA GPU detected"
            else
                is_nvidia_gpu_present="NVIDIA GPU not detected"
            fi
        else
            is_nvidia_gpu_present="NVIDIA GPU not detected"
        fi
    else
        # WSL2 detection
        for dir in "/mnt/c" "/c"; do
            if [[ -d "$dir/Windows/System32" ]]; then
                if [[ -f "$dir/Windows/System32/cmd.exe" ]]; then
                    gpu_info=$("$dir/Windows/System32/cmd.exe" /d /c "wmic path win32_VideoController get name | findstr /i nvidia" 2>/dev/null)
                    if [[ -n "$gpu_info" ]]; then
                        found=1
                        is_nvidia_gpu_present="NVIDIA GPU detected"
                        break
                    fi
                fi
            fi
        done

        if [[ "$found" -eq 0 ]]; then
            is_nvidia_gpu_present="NVIDIA GPU not detected"
        fi
    fi
}

# Find CUDA version.json file location
find_cuda_json_file() {
    local cuda_json=""
    if [[ -f "/opt/cuda/version.json" ]]; then
        cuda_json="/opt/cuda/version.json"
    elif [[ -f "/usr/local/cuda/version.json" ]]; then
        cuda_json="/usr/local/cuda/version.json"
    fi

    echo "$cuda_json"
}

# Get local CUDA version
get_local_cuda_version() {
    local cuda_json
    cuda_json=$(find_cuda_json_file)
    [[ -n "$cuda_json" && -f "$cuda_json" ]] || return 1
    jq -r '.cuda.version' < "$cuda_json" 2>/dev/null
}

# Check remote CUDA version from NVIDIA documentation
check_remote_cuda_version() {
    # Use curl to fetch the HTML content of the page
    local base_version cuda_regex html update_version

    remote_cuda_version=""
    if ! html=$(curl -fsS https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html | tr -d '\0'); then
        return 1
    fi

    # Parse the version directly from the fetched content
    cuda_regex='CUDA\ ([0-9]+\.[0-9]+)(\ Update\ ([0-9]+))?'
    if [[ "$html" =~ $cuda_regex ]]; then
        base_version="${BASH_REMATCH[1]}"
        update_version="${BASH_REMATCH[3]}"
        remote_cuda_version="$base_version"

        # Append the update number if present
        if [[ -n "$update_version" ]]; then
            remote_cuda_version+=".$update_version"
        else
            remote_cuda_version+=".0"
        fi
        return 0
    fi

    return 1
}

# Determine NVIDIA GPU architecture(s) for CUDA compilation
# Supports both single-arch (fast compile) and multi-arch (broad compatibility) modes
#
# Sets global variable: nvidia_arch_type
#   - Single mode: "compute_89,code=sm_89"
#   - Multi mode:  "-gencode arch=compute_75,code=sm_75 -gencode arch=compute_86,code=sm_86 ..."
#
# Returns: 0 on success, 1 on failure
nvidia_architecture() {
    local gpu_name compute_cap_raw compute_cap
    local -a available_archs=()
    local -a selected_archs=()

    # Prerequisite: Verify CUDA is installed
    if [[ -z $(find_cuda_json_file) ]]; then
        warn "CUDA installation not found (no version.json). Cannot determine GPU architecture."
        return 1
    fi

    # Prerequisite: Verify nvidia-smi is functional
    if ! nvidia-smi &>/dev/null; then
        echo
        warn "nvidia-smi is not responding. This typically occurs after a driver update."
        warn "Please reboot your system and run the script again."
        return 1
    fi

    # Get GPU name for logging
    gpu_name=$(nvidia-smi --query-gpu=gpu_name --format=csv,noheader 2>/dev/null | head -n1 | xargs)
    if [[ -z "$gpu_name" ]]; then
        fail "Failed to query GPU name from nvidia-smi. Line: ${LINENO}"
    fi

    # Get compute capability of installed GPU
    compute_cap_raw=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null | head -n1 | xargs)
    if [[ -n "$compute_cap_raw" && "$compute_cap_raw" =~ ^[0-9]+\.[0-9]+$ ]]; then
        compute_cap="${compute_cap_raw//./}"
    fi

    # ═══════════════════════════════════════════════════════════════════════════
    # Query nvcc for all supported architectures
    # ═══════════════════════════════════════════════════════════════════════════
    if command -v nvcc &>/dev/null; then
        # Get list of supported SM architectures from nvcc
        while IFS= read -r arch; do
            # Only include real/stable architectures (filter out experimental/future)
            # Known stable architectures: 35, 37, 50, 52, 53, 60, 61, 62, 70, 72, 75, 80, 86, 87, 89, 90, 100
            if [[ "$arch" =~ ^(3[57]|5[0-3]|6[0-2]|7[0-5]|8[0679]|90|100)$ ]]; then
                available_archs+=("$arch")
            fi
        done < <(nvcc --list-gpu-code 2>/dev/null | grep -oP 'sm_\K[0-9]+' | sort -n | uniq)
    fi

    # If no architectures found via nvcc, fall back to detected GPU only
    if [[ ${#available_archs[@]} -eq 0 ]]; then
        if [[ -n "$compute_cap" ]]; then
            # Include a PTX target for forward compatibility (CUDA best practices).
            nvidia_arch_type="-gencode arch=compute_${compute_cap},code=sm_${compute_cap} -gencode arch=compute_${compute_cap},code=compute_${compute_cap}"
            log "Detected GPU: $gpu_name (SM $compute_cap) - using single architecture + PTX"
            return 0
        else
            fail "No CUDA architectures detected and GPU compute capability unknown. Line: ${LINENO}"
        fi
    fi

    # ═══════════════════════════════════════════════════════════════════════════
    # Prompt user for architecture selection strategy
    # ═══════════════════════════════════════════════════════════════════════════
    echo
    echo "════════════════════════════════════════════════════════════════"
    echo "  CUDA Architecture Selection"
    echo "════════════════════════════════════════════════════════════════"
    echo "  Detected GPU: $gpu_name"
    [[ -n "$compute_cap" ]] && echo "  Compute Capability: $compute_cap_raw (sm_$compute_cap)"
    echo
    echo "  Available architectures from CUDA toolkit:"
    echo "    ${available_archs[*]}"
    echo
    echo "  Options:"
    echo "    1) Current GPU only (sm_${compute_cap:-??}) - Fastest compile, smallest binary"
    echo "    2) Common architectures (75,86,89) - Good compatibility, moderate compile time"
    echo "    3) All available architectures - Maximum compatibility, longest compile time"
    echo "    4) Custom selection"
    echo "════════════════════════════════════════════════════════════════"
    echo

    local choice
    while true; do
        read -rp "Select option [1-4, default=1]: " choice
        choice="${choice:-1}"

        case "$choice" in
            1)
                # Current GPU only
                if [[ -n "$compute_cap" ]]; then
                    selected_archs=("$compute_cap")
                else
                    warn "Could not detect current GPU architecture. Using common architectures instead."
                    selected_archs=(75 86 89)
                fi
                break
                ;;
            2)
                # Common architectures: Turing (75), Ampere (86), Ada (89)
                # These cover most modern GPUs (RTX 20/30/40 series)
                selected_archs=()
                for arch in 75 86 89; do
                    # Only include if supported by nvcc
                    if printf '%s\n' "${available_archs[@]}" | grep -qx "$arch"; then
                        selected_archs+=("$arch")
                    fi
                done
                [[ ${#selected_archs[@]} -eq 0 ]] && selected_archs=("${available_archs[@]}")
                break
                ;;
            3)
                # All available architectures
                selected_archs=("${available_archs[@]}")
                break
                ;;
            4)
                # Custom selection
                echo
                echo "Available architectures: ${available_archs[*]}"
                echo "Enter space-separated list of architectures to include:"
                read -rp "> " custom_input
                read -ra selected_archs <<< "$custom_input"

                # Validate selections
                local valid=true
                for arch in "${selected_archs[@]}"; do
                    if ! printf '%s\n' "${available_archs[@]}" | grep -qx "$arch"; then
                        warn "Architecture '$arch' is not available in your CUDA toolkit"
                        valid=false
                    fi
                done

                if [[ "$valid" == "true" && ${#selected_archs[@]} -gt 0 ]]; then
                    break
                else
                    warn "Please enter valid architecture numbers from: ${available_archs[*]}"
                fi
                ;;
            *)
                warn "Invalid option. Please enter 1, 2, 3, or 4."
                ;;
        esac
    done

    # ═══════════════════════════════════════════════════════════════════════════
    # Build the nvccflags string
    # ═══════════════════════════════════════════════════════════════════════════
    # Always use -gencode format for consistency
    # This format works for both single and multiple architectures
    local gencode_flags=""
    local highest_arch=""
    for arch in "${selected_archs[@]}"; do
        gencode_flags+="-gencode arch=compute_${arch},code=sm_${arch} "
        if [[ -z "$highest_arch" || "$arch" -gt "$highest_arch" ]]; then
            highest_arch="$arch"
        fi
    done
    # Add a PTX target for the highest architecture to allow forward compatibility.
    if [[ -n "$highest_arch" ]]; then
        gencode_flags+="-gencode arch=compute_${highest_arch},code=compute_${highest_arch} "
    fi
    nvidia_arch_type="${gencode_flags% }"  # Remove trailing space

    echo
    log "Selected CUDA architecture(s): ${selected_archs[*]}"
    log "nvccflags will use: $nvidia_arch_type"
    return 0
}

# Interactive CUDA toolkit installer
download_cuda() {
    local -a options=()
    local choice distro deb_file deb_url pin_url
    local cuda_version="${remote_cuda_version:-$DEFAULT_CUDA_VERSION}"
    local cuda_major cuda_minor cuda_pkg_version cuda_path_suffix cuda_prefix

    IFS='.' read -r cuda_major cuda_minor _ <<< "$cuda_version"
    cuda_pkg_version="${cuda_major}-${cuda_minor}"
    cuda_path_suffix="${cuda_major}.${cuda_minor}"
    cuda_prefix="/usr/local/cuda-${cuda_path_suffix}"

    printf "\n%s\n%s\n\n" "Pick your Linux version from the list below:" "Supported architecture: x86_64"

    options=(
        "Debian 12 (Bookworm)"
        "Debian 13 (Trixie)"
        "Ubuntu 22.04 (Jammy Jellyfish)"
        "Ubuntu 24.04 (Noble Numbat)"
        "Ubuntu WSL (Windows)"
        "Skip"
    )

    select choice in "${options[@]}"; do
        case "$choice" in
            "Debian 12 (Bookworm)")
                distro="debian12"
                ;;
            "Debian 13 (Trixie)")
                distro="debian13"
                ;;
            "Ubuntu 22.04 (Jammy Jellyfish)")
                distro="ubuntu2204"
                ;;
            "Ubuntu 24.04 (Noble Numbat)")
                distro="ubuntu2404"
                ;;
            "Ubuntu WSL (Windows)")
                distro="wsl-ubuntu"
                ;;
            "Skip")
                warn "Skipping CUDA installation."
                return 0
                ;;
            *)
                warn "Invalid selection. Please choose a valid option."
                continue
                ;;
        esac
        break
    done

    if [[ "$choice" != "Skip" ]]; then
        log "Installing CUDA $cuda_version for $choice..."

        # Use secure temporary directory with cleanup trap (restore any prior traps).
        local temp_dir
        temp_dir=$(mktemp -d) || fail "Failed to create temporary directory"

        local prev_trap_exit prev_trap_err prev_trap_int prev_trap_term
        prev_trap_exit="$(trap -p EXIT || true)"
        prev_trap_err="$(trap -p ERR || true)"
        prev_trap_int="$(trap -p INT || true)"
        prev_trap_term="$(trap -p TERM || true)"

        restore_trap() {
            local sig=$1
            local saved=$2
            if [[ -n "$saved" ]]; then
                eval "$saved"
            else
                trap - "$sig"
            fi
        }

        # Set up cleanup trap to ensure temp files are removed on any exit.
        cleanup_cuda_temp() {
            rm -rf "$temp_dir" 2>/dev/null || true
        }
        trap cleanup_cuda_temp EXIT ERR INT TERM

        # Debian 13 uses local installer method (different from keyring method)
        if [[ "$distro" == "debian13" ]]; then
            # Debian 13 uses CUDA 13.1 with local installer
            local deb13_cuda_version=13.1.0
            local deb13_driver_version=590.44.01-1
            local deb13_pkg_version=13-1
            local deb13_deb_file="cuda-repo-debian13-13-1-local_${deb13_cuda_version}-${deb13_driver_version}_amd64.deb"
            local deb13_deb_url="https://developer.download.nvidia.com/compute/cuda/${deb13_cuda_version}/local_installers/${deb13_deb_file}"
            local deb13_cuda_prefix=/usr/local/cuda-13.1

            log "Downloading CUDA ${deb13_cuda_version} local installer for Debian 13..."

            # Download the local installer package
            # Prefer aria2c (tuned for high-speed fiber connections), fall back to wget
            local download_success=false
            if command -v aria2c &>/dev/null; then
                log "Using aria2c for high-speed download..."
                if aria2c -x16 -s16 -k1M --file-allocation=none --console-log-level=warn \
                    --summary-interval=5 --download-result=full \
                    -d "$temp_dir" -o "$deb13_deb_file" "$deb13_deb_url"; then
                    download_success=true
                else
                    warn "aria2c download failed, falling back to wget..."
                fi
            fi

            if [[ "$download_success" != "true" ]]; then
                if command -v wget &>/dev/null; then
                    log "Using wget for download..."
                    if wget --show-progress -cq -O "$temp_dir/$deb13_deb_file" "$deb13_deb_url"; then
                        download_success=true
                    fi
                else
                    # Final fallback to curl
                    if curl -fL --retry 3 --retry-delay 2 --connect-timeout 15 --max-time 600 \
                        -o "$temp_dir/$deb13_deb_file" "$deb13_deb_url"; then
                        download_success=true
                    fi
                fi
            fi

            if [[ "$download_success" != "true" ]]; then
                cleanup_cuda_temp
                fail "Failed to download CUDA local installer package"
            fi

            sudo dpkg -i "$temp_dir/$deb13_deb_file" || { cleanup_cuda_temp; fail "Failed to install CUDA local repository package"; }

            # Copy the keyring from the local repo
            sudo cp -f /var/cuda-repo-debian13-13-1-local/cuda-*-keyring.gpg /usr/share/keyrings/ || warn "Failed to copy CUDA keyring"

            # Update package lists and install CUDA
            sudo apt update
            if sudo apt -y install "cuda-toolkit-${deb13_pkg_version}"; then
                log "CUDA ${deb13_cuda_version} installed successfully."
                if [[ -d "$deb13_cuda_prefix/bin" ]]; then
                    export PATH="$deb13_cuda_prefix/bin:$PATH"
                fi
                if [[ -d "$deb13_cuda_prefix/lib64" ]]; then
                    export LD_LIBRARY_PATH="$deb13_cuda_prefix/lib64:$LD_LIBRARY_PATH"
                fi
            else
                cleanup_cuda_temp
                fail "Failed to install CUDA toolkit"
            fi
        else
            # Other distros use keyring/network installer method
            deb_file="cuda-keyring_1.1-1_all.deb"
            deb_url="https://developer.download.nvidia.com/compute/cuda/repos/$distro/x86_64/$deb_file"
            pin_url="https://developer.download.nvidia.com/compute/cuda/repos/$distro/x86_64/cuda-$distro.pin"

            # Download and install the CUDA keyring
            if curl -fL --retry 3 --retry-delay 2 --connect-timeout 15 --max-time 600 -o "$temp_dir/$deb_file" "$deb_url"; then
                sudo dpkg -i "$temp_dir/$deb_file" || { cleanup_cuda_temp; fail "Failed to install CUDA keyring package"; }
            else
                cleanup_cuda_temp
                fail "Failed to download CUDA keyring package"
            fi

            # Add the CUDA repository pin
            if curl -fL --retry 3 --retry-delay 2 --connect-timeout 15 --max-time 600 -o "$temp_dir/cuda.pin" "$pin_url"; then
                sudo mv "$temp_dir/cuda.pin" /etc/apt/preferences.d/cuda-repository-pin-600
            else
                warn "Failed to download CUDA repository pin file"
            fi

            # Update package lists and install CUDA
            sudo apt update
            if sudo apt -y install "cuda-toolkit-${cuda_pkg_version}"; then
                log "CUDA $cuda_version installed successfully."
                if [[ -d "$cuda_prefix/bin" ]]; then
                    export PATH="$cuda_prefix/bin:$PATH"
                fi
                if [[ -d "$cuda_prefix/lib64" ]]; then
                    export LD_LIBRARY_PATH="$cuda_prefix/lib64:$LD_LIBRARY_PATH"
                fi
            else
                cleanup_cuda_temp
                fail "Failed to install CUDA toolkit"
            fi
        fi

        # Clean up temporary files and restore previous traps
        cleanup_cuda_temp
        restore_trap EXIT "$prev_trap_exit"
        restore_trap ERR "$prev_trap_err"
        restore_trap INT "$prev_trap_int"
        restore_trap TERM "$prev_trap_term"
    fi
}

# Main CUDA installation coordinator
install_cuda() {
    local choice

    echo -e "${CYAN}Checking GPU Status${NC}"
    echo "========================================================"
    # Reuse GPU detection results from initialize_hardware_detection() instead of
    # re-running expensive hardware probes (lshw, lspci, nvidia-smi, etc.).

    # If non-free builds are disabled, skip CUDA installation prompts entirely.
    if [[ "${NONFREE_AND_GPL:-false}" != "true" ]]; then
        if [[ "$is_nvidia_gpu_present" == "NVIDIA GPU detected" ]]; then
            warn "NVIDIA GPU detected, but CUDA/NVENC requires --enable-nonfree. Skipping CUDA install."
            gpu_flag=0
        else
            gpu_flag=1
        fi
        export gpu_flag
        return 0
    fi

    if [[ "$amd_gpu_test" == "AMD GPU detected" ]] && [[ "$is_nvidia_gpu_present" == "NVIDIA GPU not detected" ]]; then
        echo -e "${YELLOW}⚡${NC} AMD GPU detected"
        echo -e "${RED}✗${NC} NVIDIA GPU not detected"
        warn "CUDA Hardware Acceleration will not be enabled"
        gpu_flag=1
        export gpu_flag
        return 0
    elif [[ "$is_nvidia_gpu_present" == "NVIDIA GPU detected" ]]; then
        echo -e "${GREEN}✓${NC} NVIDIA GPU detected"
        echo -e "${CYAN}→${NC} Checking CUDA installation status..."
        local remote_ok=false
        if check_remote_cuda_version; then
            remote_ok=true
        else
            warn "Unable to determine latest CUDA version from NVIDIA release notes."
        fi
        local_cuda_version=$(get_local_cuda_version)

        if [[ -z "$local_cuda_version" ]]; then
            echo -e "${YELLOW}!${NC} CUDA is not currently installed"
            if [[ "$remote_ok" == "true" ]]; then
                echo -e "${CYAN}→${NC} Latest available version: ${GREEN}$remote_cuda_version${NC}"
            else
                echo -e "${CYAN}→${NC} Latest available version: ${YELLOW}Unknown${NC} (defaulting to ${GREEN}$DEFAULT_CUDA_VERSION${NC} if you install)"
            fi
            echo
            read -r -p "Do you want to install the latest CUDA version? (yes/no): " choice
            if [[ "$choice" =~ ^(yes|y)$ ]]; then
                download_cuda
                # After successful install, set gpu_flag and prompt for architecture selection
                gpu_flag=0
                export gpu_flag
                if nvidia_architecture; then
                    export nvidia_arch_type
                else
                    warn "Failed to detect NVIDIA architecture after CUDA install"
                fi
                return 0
            fi
            gpu_flag=1
            export gpu_flag
            return 0
        fi

        if [[ "$remote_ok" == "true" ]]; then
            if [[ "$local_cuda_version" == "$remote_cuda_version" ]]; then
                echo -e "${GREEN}✓${NC} CUDA ${GREEN}$local_cuda_version${NC} is installed and up to date"
                gpu_flag=0
                export gpu_flag
                return 0
            fi

            echo -e "${YELLOW}!${NC} Installed CUDA version: ${YELLOW}$local_cuda_version${NC}"
            echo -e "${CYAN}→${NC} Latest available version: ${GREEN}$remote_cuda_version${NC}"
            read -r -p "Do you want to update/reinstall CUDA to the latest version? (yes/no): " choice
            if [[ "$choice" =~ ^(yes|y)$ ]]; then
                download_cuda
                # After successful update, set gpu_flag and prompt for architecture selection
                gpu_flag=0
                export gpu_flag
                if nvidia_architecture; then
                    export nvidia_arch_type
                else
                    warn "Failed to detect NVIDIA architecture after CUDA update"
                fi
                return 0
            fi

            # User declined update, but CUDA is still installed - set flags appropriately
            gpu_flag=0
            export gpu_flag
            return 0
        fi

        echo -e "${YELLOW}!${NC} Installed CUDA version: ${YELLOW}$local_cuda_version${NC}"
        warn "Unable to check for CUDA updates. Skipping update prompt."
        gpu_flag=0
        export gpu_flag
        return 0
    else
        gpu_flag=1
        export gpu_flag
    fi
    return 0
}

# Download Windows headers for hardware acceleration
install_windows_hardware_acceleration() {
    local file
    : "${workspace:?workspace is required}"
    mkdir -p "$workspace/include"

    declare -A files=(
        ["objbase.h"]="https://raw.githubusercontent.com/wine-mirror/wine/master/include/objbase.h"
        ["dxva2api.h"]="https://download.videolan.org/pub/contrib/dxva2api.h"
        ["windows.h"]="https://raw.githubusercontent.com/tpn/winsdk-10/master/Include/10.0.10240.0/um/Windows.h"
        ["direct.h"]="https://raw.githubusercontent.com/tpn/winsdk-10/master/Include/10.0.10240.0/km/crt/direct.h"
        ["dxgidebug.h"]="https://raw.githubusercontent.com/apitrace/dxsdk/master/Include/dxgidebug.h"
        ["dxva.h"]="https://raw.githubusercontent.com/nihon-tc/Rtest/master/header/Microsoft%20SDKs/Windows/v7.0A/Include/dxva.h"
        ["intrin.h"]="https://raw.githubusercontent.com/yuikns/intrin/master/intrin.h"
        ["arm_neon.h"]="https://raw.githubusercontent.com/gcc-mirror/gcc/master/gcc/config/arm/arm_neon.h"
        ["conio.h"]="https://raw.githubusercontent.com/zoelabbb/conio.h/master/conio.h"
    )

    for file in "${!files[@]}"; do
        curl -fL --retry 3 --retry-delay 2 --connect-timeout 15 --max-time 600 \
            --output "$workspace/include/$file" "${files[$file]}" \
            || fail "Failed to download Windows header '$file'. Line: ${LINENO}"
    done
}

# Initialize hardware detection
initialize_hardware_detection() {
    echo
    echo -e "${CYAN}Detecting Hardware${NC}"
    echo "========================================================"

    # Check AMD GPU
    amd_gpu_test=$(check_amd_gpu)

    # Check NVIDIA GPU
    check_nvidia_gpu

    # Set up GPU flags and display results
    if [[ "$amd_gpu_test" == "AMD GPU detected" ]]; then
        echo -e "${YELLOW}⚡${NC} AMD GPU: ${YELLOW}Detected${NC}"
    fi

    if [[ "$is_nvidia_gpu_present" == "NVIDIA GPU detected" ]]; then
        echo -e "${GREEN}✓${NC} NVIDIA GPU: ${GREEN}Detected${NC}"
        gpu_flag=0

        # Determine NVIDIA GPU architecture for CUDA compilation
        if [[ "${NONFREE_AND_GPL:-false}" == "true" ]]; then
            if nvidia_architecture; then
                export nvidia_arch_type
                echo -e "${GREEN}✓${NC} NVIDIA architecture detected"
            else
                warn "Failed to detect NVIDIA architecture - CUDA compilation may use default settings"
            fi
        else
            warn "Skipping CUDA architecture selection (non-free builds disabled)."
        fi
    else
        echo -e "${RED}✗${NC} NVIDIA GPU: ${RED}Not detected${NC}"
        if [[ "$amd_gpu_test" != "AMD GPU detected" ]]; then
            warn "No compatible GPU detected"
        else
            warn "CUDA Hardware Acceleration will not be enabled"
        fi
        gpu_flag=1
    fi
    export gpu_flag
}
