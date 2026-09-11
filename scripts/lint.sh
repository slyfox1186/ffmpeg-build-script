#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$repo_root"

command -v shellcheck >/dev/null 2>&1 || {
    printf "'shellcheck' is required (install the 'shellcheck' package).\n" >&2
    exit 1
}
command -v python3 >/dev/null 2>&1 || {
    printf "'python3' is required.\n" >&2
    exit 1
}

shopt -s nullglob
shell_files=(build-ffmpeg.sh scripts/*.sh tests/*.sh)
text_files=(
    .gitignore
    README.md
    example.toml
    run_linter.py
    "${shell_files[@]}"
    .github/workflows/*.yml
    .github/workflows/*.yaml
)
shopt -u nullglob
((${#shell_files[@]} > 0)) || {
    printf 'No project shell scripts were found.\n' >&2
    exit 1
}

for shell_file in "${shell_files[@]}"; do
    bash -n "$shell_file"
done
printf 'bash syntax: OK (%d files)\n' "${#shell_files[@]}"

shellcheck --external-sources --severity=style "${shell_files[@]}"
printf 'ShellCheck: OK\n'

python3 -c \
    'import ast, pathlib, sys; ast.parse(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"), filename=sys.argv[1])' \
    run_linter.py
printf 'Python syntax: OK\n'

# README reproduces usage() verbatim as the CLI contract. Nothing enforced that,
# so the two drifted (column widths and one option description). Neither awk
# program may call exit: lint.sh runs under `pipefail`, and quitting early would
# hand the producer SIGPIPE and fail the whole gate.
readme_help_block="$(
    awk '
        /^## Command-line interface$/ { in_section = 1; next }
        in_section && /^```/ {
            if (seen_fence) { in_section = 0; in_block = 0; next }
            seen_fence = 1
            in_block = 1
            next
        }
        in_block { print }
    ' README.md
)"
actual_help_block="$(
    bash build-ffmpeg.sh --help |
        awk '
            /^Example:/ { capture = 0 }
            /^Actions:/ { capture = 1 }
            capture { print }
        '
)"
[[ -n "$readme_help_block" ]] ||
    { printf "No '## Command-line interface' code block was found in README.md.\n" >&2; exit 1; }
if [[ "$readme_help_block" != "$actual_help_block" ]]; then
    printf "README.md's command-line interface block no longer matches 'build-ffmpeg.sh --help'.\n" >&2
    diff -u \
        <(printf '%s\n' "$readme_help_block") \
        <(printf '%s\n' "$actual_help_block") >&2 || true
    exit 1
fi
printf 'README help text: OK\n'

# fail() ends in `exit 1`, which inside $(...) ends only the subshell: the
# caller keeps running with an empty string. The resolve_*/git_clone helpers
# therefore report with warn() and return non-zero, and every capture of one
# must check that status. Without this rule the next such call site would
# silently reintroduce the bug.
# Matched anywhere on the line, not just at the start of an assignment, so a
# nested capture like x="$(outer "$(resolve_foo)")" is caught too: there the
# outer command succeeds and the inner status is lost entirely.
unchecked_captures="$(
    grep -nE '\$\((resolve_[a-z_]+|git_clone|canonicalize_path)[[:space:]]' \
        "${shell_files[@]}" |
        grep -vE '\|\|' || true
)"
if [[ -n "$unchecked_captures" ]]; then
    printf 'Captured a status-returning helper without checking it:\n' >&2
    printf '%s\n' "$unchecked_captures" >&2
    printf "Append '|| fail \"...\"' (or '|| return 1') to each line above.\n" >&2
    exit 1
fi
printf 'Checked helper captures: OK\n'

retired_apt_interfaces=("apt""-get" "apt""-cache")
for retired_apt_interface in "${retired_apt_interfaces[@]}"; do
    if grep -nF -- "$retired_apt_interface" "${text_files[@]}" >/dev/null 2>&1; then
        printf "Retired APT interface '%s' was found in project files.\n" \
            "$retired_apt_interface" >&2
        grep -nF -- "$retired_apt_interface" "${text_files[@]}" >&2
        exit 1
    fi
done
printf 'APT interface policy: OK\n'

if grep -nE '[[:blank:]]+$' "${text_files[@]}" >/dev/null 2>&1; then
    printf 'Trailing whitespace was found in project text files.\n' >&2
    grep -nE '[[:blank:]]+$' "${text_files[@]}" >&2
    exit 1
fi
printf 'Whitespace: OK\n'
