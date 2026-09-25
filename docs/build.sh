#!/usr/bin/env bash
# Rebuild the wheel the browser app installs, and the manifest pointing at it.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -f docs/wheels/*.whl
pip wheel --no-deps -q -w docs/wheels ./          # explicit path: "pip wheel repo" would hit PyPI
W=$(basename "$(ls docs/wheels/*.whl)")
printf '{"wheel": "%s"}\n' "$W" > docs/wheels/index.json
echo "docs/wheels/$W"
