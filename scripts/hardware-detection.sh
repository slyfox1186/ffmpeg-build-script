#!/usr/bin/env bash
# shellcheck disable=SC2068,SC2162,SC2317 source=/dev/null

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

# AMD GPU detection
check_amd_gpu() {
    if lshw -C display 2>&1 | grep -Eioq "amdgpu|amd"; then
        echo "AMD GPU detected"
    elif dpkg -l 2>&1 | grep -iq "amdgpu"; then
        echo "AMD GPU detected"
    elif lspci 2>&1 | grep -i "amd"; then
        echo "AMD GPU detected"
    else
        echo "No AMD GPU detected"
    fi
}

# NVIDIA GPU detection (works in both native Linux and WSL2)
check_nvidia_gpu() {
    local found
    path_exists=0
    found=0
    gpu_info=""

    if ! grep -Eiq '(microsoft|slyfox1186)' /proc/version; then
        if lspci | grep -qi nvidia; then
            is_nvidia_gpu_present="NVIDIA GPU detected"
        else
            is_nvidia_gpu_present="NVIDIA GPU not detected"
        fi
    else
        for dir in "/mnt/c" "/c"; do
            if [[ -d "$dir/Windows/System32" ]]; then
                path_exists=1
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
    if [[ -f "/opt/cuda/version.json" ]]; then
        locate_cuda_json_file="/opt/cuda/version.json"
    elif [[ -f "/usr/local/cuda/version.json" ]]; then
        locate_cuda_json_file="/usr/local/cuda/version.json"
    fi

    echo "$locate_cuda_json_file"
}

# Get local CUDA version
get_local_cuda_version() {
    [[ -f "/usr/local/cuda/version.json" ]] && jq -r '.cuda.version' < "/usr/local/cuda/version.json"
}

# Check remote CUDA version from NVIDIA documentation
check_remote_cuda_version() {
    # Use curl to fetch the HTML content of the page
    local base_version cuda_regex html update_version

    html=$(curl -fsS "https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html" | tr -d '\0')

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
    fi
}

# Determine NVIDIA GPU architecture for CUDA compilation
nvidia_architecture() {
    if [[ -n $(find_cuda_json_file) ]]; then
        gpu_name=$(nvidia-smi --query-gpu=gpu_name --format=csv,noheader | head -n1)

        case "$gpu_name" in
            "Quadro P2000"|"NVIDIA GeForce GT 1010"|"NVIDIA GeForce GTX 1030"|"NVIDIA GeForce GTX 1050"|"NVIDIA GeForce GTX 1060"|"NVIDIA GeForce GTX 1070"|"NVIDIA GeForce GTX 1080"|"NVIDIA TITAN Xp"|"NVIDIA Tesla P40"|"NVIDIA Tesla P4")
                nvidia_arch_type="compute_61,code=sm_61"
                ;;
            "NVIDIA GeForce GTX 1180"|"NVIDIA GeForce GTX Titan V"|"Quadro GV100"|"NVIDIA Tesla V100")
                nvidia_arch_type="compute_70,code=sm_70"
                ;;
            "NVIDIA GeForce GTX 1660 Ti"|"NVIDIA GeForce RTX 2060"|"NVIDIA GeForce RTX 2070"|"NVIDIA GeForce RTX 2080"|"Quadro 4000"|"Quadro 5000"|"Quadro 6000"|"Quadro 8000"|"NVIDIA T1000"|"NVIDIA T2000"|"NVIDIA Tesla T4")
                nvidia_arch_type="compute_75,code=sm_75"
                ;;
            "NVIDIA GeForce RTX 3050"|"NVIDIA GeForce RTX 3050 Ti"|"NVIDIA GeForce RTX 3060"|"NVIDIA GeForce RTX 3060 Ti"|"NVIDIA GeForce RTX 3070"|"NVIDIA GeForce RTX 3070 Ti"|"NVIDIA GeForce RTX 3080"|"NVIDIA GeForce RTX 3080 Ti"|"NVIDIA GeForce RTX 3090"|"NVIDIA GeForce RTX 3090 Ti"|"NVIDIA RTX A2000"|"NVIDIA RTX A3000"|"NVIDIA RTX A4000"|"NVIDIA RTX A5000"|"NVIDIA RTX A6000")
                nvidia_arch_type="compute_86,code=sm_86"
                ;;
            "NVIDIA GeForce RTX 4060 Ti"|"NVIDIA GeForce RTX 4070 Ti"|"NVIDIA GeForce RTX 4080"|"NVIDIA GeForce RTX 4090")
                nvidia_arch_type="compute_89,code=sm_89"
                ;;
            "NVIDIA H100")
                nvidia_arch_type="compute_90,code=sm_90"
                ;;
            *) echo "If you get a driver version \"mismatch\" when executing the command \"nvidia-smi\", reboot your PC and rerun the script."
               echo
               fail "Failed to set the variable \"nvidia_arch_type\". Line: $LINENO, GPU_Name: $gpu_name"
               ;;
        esac
    else
        return 1
    fi
}

# Interactive CUDA toolkit installer
download_cuda() {
    local -a options=()
    local choice distro installer_version deb_file deb_url pin_url
    local cuda_version="${remote_cuda_version:-12.8.1}"
    local cuda_major cuda_minor cuda_patch cuda_pkg_version cuda_path_suffix cuda_prefix

    IFS='.' read -r cuda_major cuda_minor cuda_patch <<< "$cuda_version"
    cuda_pkg_version="${cuda_major}-${cuda_minor}"
    cuda_path_suffix="${cuda_major}.${cuda_minor}"
    cuda_prefix="/usr/local/cuda-${cuda_path_suffix}"

    printf "\n%s\n%s\n\n" "Pick your Linux version from the list below:" "Supported architecture: x86_64"

    options=(
        "Debian 12 (Bookworm)"
        "Ubuntu 20.04 (Focal Fossa)"
        "Ubuntu 22.04 (Jammy Jellyfish)"
        "Ubuntu 24.04 (Noble Numbat)"
        "Ubuntu WSL (Windows)"
        "Skip"
    )

    select choice in "${options[@]}"; do
        case "$choice" in
            "Debian 12 (Bookworm)")
                distro="debian12"
                installer_version="${cuda_version}"
                ;;
            "Ubuntu 20.04 (Focal Fossa)")
                distro="ubuntu2004"
                installer_version="${cuda_version}"
                ;;
            "Ubuntu 22.04 (Jammy Jellyfish)")
                distro="ubuntu2204"
                installer_version="${cuda_version}"
                ;;
            "Ubuntu 24.04 (Noble Numbat)")
                distro="ubuntu2404"
                installer_version="${cuda_version}"
                ;;
            "Ubuntu WSL (Windows)")
                distro="wsl-ubuntu"
                installer_version="${cuda_version}"
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
        deb_file="cuda-keyring_1.1-1_all.deb"
        deb_url="https://developer.download.nvidia.com/compute/cuda/repos/$distro/x86_64/$deb_file"
        pin_url="https://developer.download.nvidia.com/compute/cuda/repos/$distro/x86_64/cuda-$distro.pin"

        log "Installing CUDA $cuda_version for $choice..."
        
        # Download and install the CUDA keyring
        if curl -LSso "/tmp/$deb_file" "$deb_url"; then
            sudo dpkg -i "/tmp/$deb_file" || fail "Failed to install CUDA keyring package"
        else
            fail "Failed to download CUDA keyring package"
        fi

        # Add the CUDA repository pin
        if curl -LSso "/tmp/cuda.pin" "$pin_url"; then
            sudo mv "/tmp/cuda.pin" "/etc/apt/preferences.d/cuda-repository-pin-600"
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
            fail "Failed to install CUDA toolkit"
        fi

        # Clean up temporary files
        rm -f "/tmp/$deb_file" "/tmp/cuda.pin"
    fi
}

# Main CUDA installation coordinator
install_cuda() {
    local choice

    echo "Checking GPU Status"
    echo "========================================================"
    amd_gpu_test=$(check_amd_gpu)
    check_nvidia_gpu

    if [[ -n "$amd_gpu_test" ]] && [[ "$is_nvidia_gpu_present" == "NVIDIA GPU not detected" ]]; then
        log "AMD GPU detected."
        log "Nvidia GPU not detected"
        warn "CUDA Hardware Acceleration will not be enabled"
        return 0
    elif [[ "$is_nvidia_gpu_present" == "NVIDIA GPU detected" ]]; then
        log "Nvidia GPU detected"
        log "Determining if CUDA is installed..."
        check_remote_cuda_version
        local_cuda_version=$(get_local_cuda_version)

        if [[ -z "$local_cuda_version" ]]; then
            echo "The latest CUDA version available is: $remote_cuda_version"
            echo "CUDA is not currently installed."
            echo
            read -p "Do you want to install the latest CUDA version? (yes/no): " choice
            [[ "$choice" =~ ^(yes|y)$ ]] && download_cuda
        elif [[ "$local_cuda_version" == "$remote_cuda_version" ]]; then
            log "CUDA is already installed and up to date."
            return 0
        else
            echo "The installed CUDA version is: $local_cuda_version"
            echo "The latest CUDA version available is: $remote_cuda_version"
            read -p "Do you want to update/reinstall CUDA to the latest version? (yes/no): " choice
            [[ "$choice" =~ ^(yes|y)$ ]] && download_cuda || return 0
        fi
    else
        gpu_flag=1
    fi
    return 0
}

# Download Windows headers for hardware acceleration
install_windows_hardware_acceleration() {
    local file

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
        curl -LSso "$workspace/include/$file" "${files[$file]}"
    done
}

# Initialize hardware detection
initialize_hardware_detection() {
    echo "Checking GPU Status"
    echo "========================================================"
    
    # Check AMD GPU
    amd_gpu_test=$(check_amd_gpu)
    
    # Check NVIDIA GPU
    check_nvidia_gpu
    
    # Set up GPU flags
    if [[ -n "$amd_gpu_test" ]] && [[ "$is_nvidia_gpu_present" == "NVIDIA GPU not detected" ]]; then
        log "AMD GPU detected."
        log "NVIDIA GPU not detected"
        warn "CUDA Hardware Acceleration will not be enabled"
        gpu_flag=1
    elif [[ "$is_nvidia_gpu_present" == "NVIDIA GPU detected" ]]; then
        log "NVIDIA GPU detected"
        gpu_flag=0
    else
        log "No compatible GPU detected"
        gpu_flag=1
    fi
    
    log "Hardware detection completed"
}
