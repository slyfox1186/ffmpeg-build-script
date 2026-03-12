#!/usr/bin/env bash

set -o pipefail

find_highest_apt_package_version() {
    local regex="${1:-}" package_name

    [[ -n "$regex" ]] || return 1
    command -v apt-cache >/dev/null 2>&1 || return 1

    package_name="$(apt-cache pkgnames 2>/dev/null | grep -xE "$regex" | sort -V | tail -n 1)"
    [[ -n "$package_name" ]] || return 1

    printf '%s\n' "${package_name##*-}"
}

append_search_root() {
    local candidate="${1:-}"

    [[ -n "$candidate" ]] || return 0
    [[ -d "$candidate" ]] || return 0

    SEARCH_ROOTS+=("$candidate")
}

append_globbed_search_roots() {
    local pattern="${1:-}" match

    [[ -n "$pattern" ]] || return 0

    while IFS= read -r match; do
        append_search_root "$match"
    done < <(compgen -G "$pattern" 2>/dev/null || true)
}

collect_search_roots() {
    local path_dir custom_dir

    SEARCH_ROOTS=()

    IFS=':' read -r -a PATH_DIRS <<< "${PATH:-}"
    for path_dir in "${PATH_DIRS[@]}"; do
        append_search_root "$path_dir"
    done

    append_search_root "/usr/bin"
    append_search_root "/usr/local/bin"
    append_search_root "/opt/bin"
    append_search_root "$HOME/bin"
    append_search_root "$HOME/.local/bin"

    append_globbed_search_roots "/opt/*/bin"
    append_globbed_search_roots "/opt/llvm*/bin"
    append_globbed_search_roots "$HOME/opt/*/bin"
    append_globbed_search_roots "$HOME/toolchains/*/bin"

    if [[ -n "${COMPILER_SEARCH_DIRS:-}" ]]; then
        IFS=':' read -r -a CUSTOM_DIRS <<< "$COMPILER_SEARCH_DIRS"
        for custom_dir in "${CUSTOM_DIRS[@]}"; do
            append_globbed_search_roots "$custom_dir"
            append_search_root "$custom_dir"
        done
    fi
}

compiler_patterns_for() {
    local compiler_name="${1:-}"

    case "$compiler_name" in
        gcc)
            printf '%s\n' 'gcc' 'gcc-[0-9]*'
            ;;
        g++)
            printf '%s\n' 'g++' 'g++-[0-9]*'
            ;;
        clang)
            printf '%s\n' 'clang' 'clang-[0-9]*'
            ;;
        clang++)
            printf '%s\n' 'clang++' 'clang++-[0-9]*'
            ;;
        *)
            return 1
            ;;
    esac
}

resolve_binary_version() {
    local compiler_name="${1:-}" compiler_path="${2:-}" version

    [[ -n "$compiler_name" ]] || return 1
    [[ -n "$compiler_path" ]] || return 1
    [[ -x "$compiler_path" ]] || return 1

    case "$compiler_name" in
        gcc|g++)
            version="$("$compiler_path" -dumpfullversion -dumpversion 2>/dev/null | head -n 1)"
            ;;
        clang|clang++)
            version="$("$compiler_path" --version 2>/dev/null | head -n 1 | grep -oE '[0-9]+(\.[0-9]+){0,2}' | head -n 1)"
            ;;
        *)
            return 1
            ;;
    esac

    [[ -n "$version" ]] || return 1
    printf '%s\n' "$version"
}

discover_installed_highest() {
    local compiler_name="${1:-}" search_root pattern candidate resolved_path version best_version best_path

    declare -A seen_paths=()

    collect_search_roots

    for search_root in "${SEARCH_ROOTS[@]}"; do
        [[ -d "$search_root" ]] || continue

        while IFS= read -r pattern; do
            shopt -s nullglob
            for candidate in "$search_root"/$pattern; do
                [[ -x "$candidate" ]] || continue
                resolved_path="$(readlink -f -- "$candidate" 2>/dev/null || printf '%s\n' "$candidate")"
                [[ -n "${seen_paths[$resolved_path]:-}" ]] && continue
                seen_paths["$resolved_path"]=1

                version="$(resolve_binary_version "$compiler_name" "$candidate" || true)"
                [[ -n "$version" ]] || continue

                if [[ -z "$best_version" ]] || [[ "$(printf '%s\n%s\n' "$best_version" "$version" | sort -V | tail -n 1)" == "$version" ]]; then
                    best_version="$version"
                    best_path="$candidate"
                fi
            done
            shopt -u nullglob
        done < <(compiler_patterns_for "$compiler_name")
    done

    [[ -n "$best_version" ]] || return 1
    printf '%s|%s\n' "$best_version" "$best_path"
}

repo_highest_for() {
    local compiler_name="${1:-}" apt_regex

    case "$compiler_name" in
        gcc)
            apt_regex='gcc-[0-9]+'
            ;;
        g++)
            apt_regex='g\+\+-[0-9]+'
            ;;
        clang|clang++)
            apt_regex='clang-[0-9]+'
            ;;
        *)
            return 1
            ;;
    esac

    find_highest_apt_package_version "$apt_regex"
}

main() {
    local compiler_name installed_result installed_version installed_path repo_version

    for compiler_name in gcc g++ clang clang++; do
        installed_result="$(discover_installed_highest "$compiler_name" || true)"
        repo_version="$(repo_highest_for "$compiler_name" || true)"

        installed_version="${installed_result%%|*}"
        installed_path="${installed_result#*|}"

        if [[ -z "$installed_result" ]]; then
            installed_version="unavailable"
            installed_path="unavailable"
        fi

        printf '%s installed_highest=%s installed_path=%s repo_highest=%s\n' \
            "$compiler_name" \
            "$installed_version" \
            "$installed_path" \
            "${repo_version:-unavailable}"
    done
}

main "$@"
