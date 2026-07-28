#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$repo_root"

command -v shellcheck >/dev/null 2>&1 || {
    printf 'shellcheck is required (install the shellcheck package).\n' >&2
    exit 1
}
command -v python3 >/dev/null 2>&1 || {
    printf 'python3 is required.\n' >&2
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

if grep -nE '[[:blank:]]+$' "${text_files[@]}" >/dev/null 2>&1; then
    printf 'Trailing whitespace was found in project text files.\n' >&2
    grep -nE '[[:blank:]]+$' "${text_files[@]}" >&2
    exit 1
fi
printf 'Whitespace: OK\n'
