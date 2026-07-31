#!/usr/bin/env bash

set -o pipefail

usage() {
    printf 'Usage: %s\n' "${0##*/}" >&2
}

append_search_root() {
    local candidate="${1:-}"
    local canonical

    [[ -n "$candidate" && "$candidate" == /* && -d "$candidate" ]] || return 0
    canonical="$(readlink -f -- "$candidate" 2>/dev/null || printf '%s' "$candidate")"
    if [[ -z "${_SEARCH_ROOT_SEEN[$canonical]+x}" ]]; then
        _SEARCH_ROOT_SEEN["$canonical"]=1
        SEARCH_ROOTS+=("$canonical")
    fi
}

collect_search_roots() {
    local directory pattern match
    local user_home="${HOME:-}"
    local -a path_directories=()
    local -a custom_directories=()

    SEARCH_ROOTS=()
    declare -gA _SEARCH_ROOT_SEEN=()
    IFS=: read -r -a path_directories <<<"${PATH:-}"
    for directory in "${path_directories[@]}"; do
        append_search_root "$directory"
    done
    for directory in /usr/bin /usr/local/bin /opt/bin \
        "${user_home:+$user_home/bin}" "${user_home:+$user_home/.local/bin}"; do
        append_search_root "$directory"
    done

    for pattern in /opt/\*/bin /opt/llvm\*/bin; do
        while IFS= read -r match; do
            append_search_root "$match"
        done < <(compgen -G "$pattern" 2>/dev/null || true)
    done
    if [[ -n "$user_home" ]]; then
        for pattern in "$user_home"/opt/\*/bin "$user_home"/toolchains/\*/bin; do
            while IFS= read -r match; do
                append_search_root "$match"
            done < <(compgen -G "$pattern" 2>/dev/null || true)
        done
    fi

    if [[ -n "${COMPILER_SEARCH_DIRS:-}" ]]; then
        IFS=: read -r -a custom_directories <<<"$COMPILER_SEARCH_DIRS"
        for directory in "${custom_directories[@]}"; do
            append_search_root "$directory"
        done
    fi
}

compiler_basename_matches() {
    local compiler_name="${1:-}" basename="${2:-}"

    case "$compiler_name" in
        gcc) [[ "$basename" =~ ^gcc(-[0-9]+)?$ ]] ;;
        g++) [[ "$basename" =~ ^g\+\+(-[0-9]+)?$ ]] ;;
        clang) [[ "$basename" =~ ^clang(-[0-9]+)?$ ]] ;;
        clang++) [[ "$basename" =~ ^clang\+\+(-[0-9]+)?$ ]] ;;
        *) return 1 ;;
    esac
}

compiler_version() {
    local compiler_name="${1:-}" binary="${2:-}"
    local version

    [[ -x "$binary" ]] || return 1
    case "$compiler_name" in
        gcc|g++)
            version="$("$binary" -dumpfullversion -dumpversion 2>/dev/null | sed -n '1p')"
            ;;
        clang|clang++)
            version="$(
                "$binary" --version 2>/dev/null |
                    sed -n '1p' |
                    grep -oE '[0-9]+(\.[0-9]+){0,2}' |
                    sed -n '1p'
            )"
            ;;
        *)
            return 1
            ;;
    esac
    [[ "$version" =~ ^[0-9]+(\.[0-9]+){0,3}$ ]] || return 1
    printf '%s\n' "$version"
}

discover_installed_highest() {
    local compiler_name="${1:-}"
    local root candidate basename resolved version
    local best_version="" best_path=""
    local -A seen_binaries=()

    for root in "${SEARCH_ROOTS[@]}"; do
        while IFS= read -r -d '' candidate; do
            basename="${candidate##*/}"
            compiler_basename_matches "$compiler_name" "$basename" || continue
            [[ -x "$candidate" ]] || continue
            resolved="$(readlink -f -- "$candidate" 2>/dev/null || printf '%s' "$candidate")"
            [[ -z "${seen_binaries[$resolved]+x}" ]] || continue
            seen_binaries["$resolved"]=1
            version="$(compiler_version "$compiler_name" "$candidate" || true)"
            [[ -n "$version" ]] || continue
            if [[ -z "$best_version" ||
                ( "$version" != "$best_version" &&
                  "$(printf '%s\n%s\n' "$best_version" "$version" | sort -V | tail -n1)" == "$version" ) ]]; then
                best_version="$version"
                best_path="$candidate"
            fi
        done < <(find "$root" -maxdepth 1 \( -type f -o -type l \) -print0 2>/dev/null)
    done

    [[ -n "$best_version" ]] || return 1
    printf '%s|%s\n' "$best_version" "$best_path"
}

highest_repository_major() {
    local compiler_name="${1:-}" package_glob package_regex package

    command -v apt >/dev/null 2>&1 || return 1
    case "$compiler_name" in
        gcc)
            package_glob='gcc-*'
            package_regex='^gcc-[0-9]+$'
            ;;
        g++)
            package_glob='g++-*'
            package_regex='^g\+\+-[0-9]+$'
            ;;
        clang|clang++)
            package_glob='clang-*'
            package_regex='^clang-[0-9]+$'
            ;;
        *) return 1 ;;
    esac
    package="$(
        apt -o APT::Cmd::Disable-Script-Warning=1 list "$package_glob" 2>/dev/null |
            sed -n 's#/.*##p' |
            grep -E "$package_regex" |
            sort -V |
            tail -n1
    )"
    [[ -n "$package" ]] || return 1
    printf '%s\n' "${package##*-}"
}

main() {
    local compiler installed version path repository

    (($# == 0)) || {
        usage
        return 2
    }
    collect_search_roots
    for compiler in gcc g++ clang clang++; do
        installed="$(discover_installed_highest "$compiler" || true)"
        repository="$(highest_repository_major "$compiler" || true)"
        if [[ -n "$installed" ]]; then
            version="${installed%%|*}"
            path="${installed#*|}"
        else
            version=unavailable
            path=unavailable
        fi
        printf '%s installed_highest=%s installed_path=%q repo_highest=%s\n' \
            "$compiler" "$version" "$path" "${repository:-unavailable}"
    done
}

main "$@"
