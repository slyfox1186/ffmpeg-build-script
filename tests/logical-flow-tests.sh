#!/usr/bin/env bash
# shellcheck disable=SC2030,SC2031
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

fail_test() {
    printf 'not ok - %s\n' "$1" >&2
    exit 1
}

assert_contains() {
    local haystack=$1
    local needle=$2
    local message=$3

    [[ "$haystack" == *"$needle"* ]] || fail_test "$message"
}

test_apt_pkgs_accepts_all_extra_package_arguments() {
    local checked_file output
    checked_file="$(mktemp)"

    (
        source "$repo_root/scripts/system-setup.sh"

        dpkg-query() {
            return 1
        }

        apt-cache() {
            case "${1:-}" in
                search)
                    return 0
                    ;;
                show)
                    printf '%s\n' "${2:-}" >> "$checked_file"
                    return 1
                    ;;
                *)
                    return 1
                    ;;
            esac
        }

        sudo() {
            fail "sudo should not be called when every package is unavailable"
        }

        apt_pkgs first-extra second-extra "third-extra fourth-extra" >/dev/null
    )

    output="$(<"$checked_file")"
    rm -f "$checked_file"

    assert_contains "$output" "first-extra" "apt_pkgs did not check first extra package"
    assert_contains "$output" "second-extra" "apt_pkgs ignored a separate extra package argument"
    assert_contains "$output" "third-extra" "apt_pkgs ignored a package from a space-separated argument"
    assert_contains "$output" "fourth-extra" "apt_pkgs ignored the final package from a space-separated argument"
}

test_github_version_helper_honors_filters_and_index() {
    local version

    version="$(
        source "$repo_root/scripts/shared-utils.sh"

        github_refs_html() {
            case "${1:-}" in
                "example/project")
                    cat <<'JSON'
<a href="/example/project/releases/tag/v2.0.0">v2.0.0</a>
<a href="/example/project/releases/tag/v1.9.0-rc1">v1.9.0-rc1</a>
<a href="/example/project/releases/tag/v1.5.0">v1.5.0</a>
<a href="/example/project/releases/tag/release-3.0.0">release-3.0.0</a>
JSON
                    ;;
                *)
                    return 1
                    ;;
            esac
        }

        # If this regresses to the legacy scraper path, keep the failure deterministic.
        # shellcheck disable=SC2317
        bash() {
            printf '9.9.9\n'
        }

        run_github_version_helper "example/project" "releases" "v" "rc" '^[0-9]+(\.[0-9]+){2}$' "2"
    )"

    [[ "$version" == "1.5.0" ]] || fail_test "GitHub version helper returned '$version', expected '1.5.0'"
}

test_github_tag_version_helper_scrapes_html_without_api() {
    local version

    version="$(
        source "$repo_root/scripts/shared-utils.sh"

        github_refs_html() {
            cat <<'EOF'
<a href="/example/project/tree/v2.5.2">v2.5.2</a>
<a href="/example/project/archive/refs/tags/v2.5.3-rc1.tar.gz">v2.5.3-rc1</a>
<a href="/example/project/archive/refs/tags/v2.4.0.zip">v2.4.0</a>
EOF
        }

        run_github_version_helper "example/project" "tags" "v" "rc" '^[0-9]+(\.[0-9]+){2}$' "1"
    )"

    [[ "$version" == "2.5.2" ]] || fail_test "GitHub tag scraper returned '$version', expected '2.5.2'"
}

test_cuda_architecture_selection_runs_once_after_cuda_update_flow() {
    local output prompt_count

    output="$(
        source "$repo_root/scripts/hardware-detection.sh"

        NONFREE_AND_GPL=true
        amd_gpu_test=""
        is_nvidia_gpu_present=""
        nvidia_arch_type=""
        arch_prompt_count=0

        check_amd_gpu() {
            printf 'AMD GPU detected\n'
        }

        check_nvidia_gpu() {
            is_nvidia_gpu_present="NVIDIA GPU detected"
        }

        check_remote_cuda_version() {
            remote_cuda_version="13.2.0"
            return 0
        }

        get_local_cuda_version() {
            printf '13.1.0\n'
        }

        download_cuda() {
            return 0
        }

        nvidia_architecture() {
            ((arch_prompt_count++))
            nvidia_arch_type="-gencode arch=compute_89,code=sm_89"
            return 0
        }

        initialize_hardware_detection >/dev/null
        install_cuda <<< "yes" >/dev/null
        printf '%s\n' "$arch_prompt_count"
    )"

    prompt_count="$(printf '%s\n' "$output" | tail -n1)"
    [[ "$prompt_count" == "1" ]] || fail_test "CUDA architecture selection ran $prompt_count times, expected once"
}

test_cuda_update_prompt_is_skipped_when_local_version_is_newer() {
    local output

    output="$(
        source "$repo_root/scripts/hardware-detection.sh"

        NONFREE_AND_GPL=true
        amd_gpu_test=""
        is_nvidia_gpu_present=""
        nvidia_arch_type=""
        download_count=0
        arch_prompt_count=0

        check_amd_gpu() {
            printf 'AMD GPU detected\n'
        }

        check_nvidia_gpu() {
            is_nvidia_gpu_present="NVIDIA GPU detected"
        }

        check_remote_cuda_version() {
            remote_cuda_version="13.2.0"
            return 0
        }

        get_local_cuda_version() {
            printf '13.2.1\n'
        }

        download_cuda() {
            ((download_count++))
            return 0
        }

        nvidia_architecture() {
            ((arch_prompt_count++))
            nvidia_arch_type="-gencode arch=compute_89,code=sm_89"
            return 0
        }

        initialize_hardware_detection >/dev/null
        install_cuda <<< "yes"
        printf 'downloads=%s arch_prompts=%s\n' "$download_count" "$arch_prompt_count"
    )"

    [[ "$output" != *"Do you want to update/reinstall CUDA"* ]] || fail_test "CUDA update prompt was shown even though local CUDA is newer"
    [[ "$output" == *"downloads=0 arch_prompts=1"* ]] || fail_test "Unexpected CUDA flow counters: $output"
}

test_vapoursynth_build_uses_meson_for_current_releases() {
    local block

    block="$(
        awk '
            /# Build VapourSynth/ { capture = 1 }
            /# Build libgav1/ { capture = 0 }
            capture { print }
        ' "$repo_root/scripts/video-libraries.sh"
    )"

    assert_contains "$block" "meson_ninja_install" "VapourSynth current releases must build with Meson"
    [[ "$block" != *"ensure_autotools"* ]] || fail_test "VapourSynth build still uses Autotools"
    [[ "$block" != *"execute sh configure"* ]] || fail_test "VapourSynth build still executes configure"
}

test_nv_codec_headers_versions_are_scraped_from_releases_html() {
    local output

    output="$(
        source "$repo_root/scripts/video-libraries.sh"

        github_refs_html() {
            [[ "${1:-}" == "FFmpeg/nv-codec-headers" ]] || return 1
            [[ "${2:-}" == "releases" ]] || return 1

            cat <<'EOF'
<relative-time datetime="2025-01-30T23:19:01Z"></relative-time>
<a href="/FFmpeg/nv-codec-headers/releases/tag/n13.0.19.0">n13.0.19.0</a>
<relative-time datetime="2024-03-31T16:51:16Z"></relative-time>
<a href="/FFmpeg/nv-codec-headers/releases/tag/n12.2.72.0">n12.2.72.0</a>
EOF
        }

        fetch_nv_codec_headers_versions
        printf '%s\n' "${sorted_versions_and_dates[@]}"
    )"

    assert_contains "$output" "13.0.19.0;01-30-2025" "nv-codec-headers latest release was not parsed from HTML"
    assert_contains "$output" "12.2.72.0;03-31-2024" "nv-codec-headers older release was not parsed from HTML"
}

test_github_version_detection_does_not_use_api() {
    local matches
    local api_host_pattern='api[.]github[.]com'
    local api_helper_pattern='github_''api_json'

    matches="$(
        grep -RInE "$api_host_pattern|$api_helper_pattern" "$repo_root/scripts" || true
    )"

    [[ -z "$matches" ]] || fail_test "GitHub API usage remains in version detection: $matches"
}

test_apt_pkgs_accepts_all_extra_package_arguments
printf 'ok - apt_pkgs accepts all extra package argument forms\n'

test_github_version_helper_honors_filters_and_index
printf 'ok - GitHub version helper honors prefix, exclude pattern, URL type, and index\n'

test_github_tag_version_helper_scrapes_html_without_api
printf 'ok - GitHub tag version helper scrapes HTML without API\n'

test_cuda_architecture_selection_runs_once_after_cuda_update_flow
printf 'ok - CUDA architecture selection runs once after CUDA update flow\n'

test_cuda_update_prompt_is_skipped_when_local_version_is_newer
printf 'ok - CUDA update prompt is skipped when local version is newer\n'

test_vapoursynth_build_uses_meson_for_current_releases
printf 'ok - VapourSynth current releases build with Meson\n'

test_nv_codec_headers_versions_are_scraped_from_releases_html
printf 'ok - nv-codec-headers versions are scraped from releases HTML\n'

test_github_version_detection_does_not_use_api
printf 'ok - GitHub version detection does not use the GitHub API\n'
