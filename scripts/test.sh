#!/bin/sh
# Run the test suite with coverage. Works both inside the docker `test` service
# (Postgres unreachable → SQLite in-memory via TESTING=1) and locally.

set -e

export TESTING=1
export DJANGO_SETTINGS_MODULE=sunnyValeConnect.settings

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/myapp"

# Prefer the local poetry-managed venv if it exists; otherwise rely on PATH.
if [ -x ".venv/bin/coverage" ]; then
    COVERAGE=".venv/bin/coverage"
elif command -v coverage >/dev/null 2>&1; then
    COVERAGE="coverage"
else
    echo "❌ 'coverage' not installed. Run: poetry install --with dev" >&2
    exit 1
fi

"$COVERAGE" erase
"$COVERAGE" run -m pytest "$@"
"$COVERAGE" report
"$COVERAGE" xml -o coverage.xml
echo "✅ Tests passed. Coverage XML written to myapp/coverage.xml"
