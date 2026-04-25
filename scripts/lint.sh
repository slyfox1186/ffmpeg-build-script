#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

files=(build-ffmpeg.sh scripts/*.sh)

for f in "${files[@]}"; do
  bash -n "$f"
done
echo "bash -n: OK"

bash tests/logical-flow-tests.sh
echo "logical flow tests: OK"

if command -v shellcheck >/dev/null 2>&1; then
  shellcheck -x "${files[@]}" tests/logical-flow-tests.sh
  echo "shellcheck: OK"
else
  echo "shellcheck not installed; skipping"
fi
