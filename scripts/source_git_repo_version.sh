#!/usr/bin/env bash

set -o pipefail

usage() {
    printf 'Usage: %s <https-git-url> [tag-prefix]\n' "${0##*/}" >&2
}

latest_stable_version() {
    local repository_url="${1:-}"
    local prefix="${2-}"
    local timeout_seconds="${GIT_OPERATION_TIMEOUT:-120}"
    local ref tag version
    local -a versions=()

    [[ "$repository_url" == https://* ]] || {
        printf 'Repository URL must use HTTPS.\n' >&2
        return 1
    }
    [[ ! "$repository_url" =~ [[:cntrl:]] && ! "$prefix" =~ [[:cntrl:]] ]] || {
        printf 'Repository URL and tag prefix may not contain control characters.\n' >&2
        return 1
    }
    [[ "$timeout_seconds" =~ ^[1-9][0-9]*$ ]] || {
        printf "'GIT_OPERATION_TIMEOUT' must be a positive integer.\n" >&2
        return 1
    }
    command -v git >/dev/null 2>&1 || {
        printf "'git' is required.\n" >&2
        return 1
    }
    command -v timeout >/dev/null 2>&1 || {
        printf "'timeout' is required.\n" >&2
        return 1
    }

    while IFS= read -r ref; do
        tag="${ref#refs/tags/}"
        [[ "$tag" != *'^{}' ]] || continue
        [[ ! "$tag" =~ (^|[-_.])(alpha|beta|dev|pre|preview|rc)[-_.0-9]*$ ]] || continue

        if [[ -n "$prefix" ]]; then
            [[ "$tag" == "$prefix"* ]] || continue
            version="${tag#"$prefix"}"
        else
            version="$tag"
            version="${version#"${version%%[0-9]*}"}"
        fi
        [[ "$version" =~ ^[0-9]+(\.[0-9]+){1,3}$ ]] || continue
        versions+=("$version")
    done < <(
        timeout --foreground "$timeout_seconds" \
            env GIT_TERMINAL_PROMPT=0 \
            git -c protocol.allow=never -c protocol.https.allow=always \
            ls-remote --tags --refs "$repository_url" 2>/dev/null |
            awk '{print $2}'
    )

    ((${#versions[@]} > 0)) || return 1
    printf '%s\n' "${versions[@]}" | sort -ruV | sed -n '1p'
}

main() {
    (($# >= 1 && $# <= 2)) || {
        usage
        return 2
    }
    latest_stable_version "$@" || {
        printf "No stable numeric release tag found for '%s'.\n" "$1" >&2
        return 1
    }
}

main "$@"
