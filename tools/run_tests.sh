#!/bin/bash
# run_tests.sh — run the MVP test suite and (optionally) write a report.
#
#   tools/run_tests.sh                 # run the tests, print the summary
#   tools/run_tests.sh --report        # also write test-results/<timestamp>/
#   tools/run_tests.sh --report --m0   # include the M0 environment gate
#
# The report directory is meant to be committed and pushed: it carries the
# human summary plus every raw log, so results travel as files instead of
# pasted text. See docs/MVP-PLAN.md.

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

PYTHON="${PYTHON:-$REPO/.venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
    PYTHON="$(command -v python3)"
fi

# pytest is not in the runtime dependency set, so a fresh venv does not have it.
# The first M0 run on the GPU box reported only "No module named pytest" and an
# empty report — check first and say something useful.
if ! "$PYTHON" -c "import pytest" >/dev/null 2>&1; then
    echo "pytest is not installed for $PYTHON — installing it now."
    if command -v uv >/dev/null 2>&1; then
        UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uvcache}" \
            uv pip install --python "$PYTHON" pytest >/dev/null 2>&1
    fi
    if ! "$PYTHON" -c "import pytest" >/dev/null 2>&1; then
        "$PYTHON" -m pip install pytest >/dev/null 2>&1 || true
    fi
    if ! "$PYTHON" -c "import pytest" >/dev/null 2>&1; then
        echo ""
        echo "Could not install pytest. Install it yourself, then re-run:"
        echo "    uv pip install --python $PYTHON pytest"
        echo "    # or: $PYTHON -m pip install pytest"
        echo "    # or: uv sync --extra test"
        echo ""
        echo "Without it the test suite cannot run at all."
        exit 3
    fi
    echo "pytest installed."
    echo ""
fi

WANT_REPORT=0
WANT_M0=0
for arg in "$@"; do
    case "$arg" in
        --report) WANT_REPORT=1 ;;
        --m0)     WANT_M0=1 ;;
        -h|--help)
            sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) echo "unknown option: $arg" >&2; exit 2 ;;
    esac
done

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="test-results/$STAMP"
if [ "$WANT_REPORT" = "1" ]; then
    mkdir -p "$OUT/raw"
fi

echo "=============================================================="
echo " NeuralScreen MVP — test run $STAMP"
echo "=============================================================="
echo "python:  $PYTHON"
echo "pytest:  $("$PYTHON" -m pytest --version 2>&1 | head -1)"
echo "repo:    $REPO"
echo "git:     $(git rev-parse --short HEAD 2>/dev/null || echo '?') $(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
echo ""

# --- environment facts worth having in the report ---------------------------
ENV_FILE="$OUT/raw/environment.txt"
env_report() {
    echo "date:      $(date -u)"
    echo "hostname:  $(hostname)"
    echo "uname:     $(uname -a)"
    echo "python:    $("$PYTHON" --version 2>&1)"
    echo "session:   XDG_SESSION_TYPE=${XDG_SESSION_TYPE:-unset} DISPLAY=${DISPLAY:-unset} WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-unset}"
    echo "desktop:   ${XDG_CURRENT_DESKTOP:-unset}"
    echo ""
    echo "--- GPU ---"
    if command -v nvidia-smi >/dev/null 2>&1; then
        nvidia-smi --query-gpu=index,name,driver_version,memory.total,compute_cap \
                   --format=csv 2>&1
    else
        echo "nvidia-smi not found"
    fi
    echo ""
    echo "--- graphics stack ---"
    for tool in wine winecfg vulkaninfo glxinfo; do
        if command -v "$tool" >/dev/null 2>&1; then
            printf '%-12s %s\n' "$tool" "$(command -v "$tool")"
        else
            printf '%-12s %s\n' "$tool" "NOT INSTALLED"
        fi
    done
    if command -v wine >/dev/null 2>&1; then
        echo "wine:       $(wine --version 2>&1)"
    fi
    echo ""
    echo "--- native/ ---"
    ls -la native/ 2>&1
    echo ""
    echo "--- vulkan ICDs ---"
    ls /usr/share/vulkan/icd.d/ 2>&1 || echo "(none)"
}

if [ "$WANT_REPORT" = "1" ]; then
    env_report > "$ENV_FILE" 2>&1
fi
env_report | sed 's/^/  /'

# --- the suite --------------------------------------------------------------
echo ""
echo "=============================================================="
echo " pytest"
echo "=============================================================="

PYTEST_ARGS=(-m pytest tests/ -v --tb=short -p no:cacheprovider)

if [ "$WANT_M0" = "1" ]; then
    export NX_RUN_M0=1
    echo "(M0 environment gate included: NX_RUN_M0=1)"
else
    echo "(M0 skipped — pass --m0 to include it)"
fi
echo ""

if [ "$WANT_REPORT" = "1" ]; then
    "$PYTHON" "${PYTEST_ARGS[@]}" 2>&1 | tee "$OUT/raw/pytest.txt"
    STATUS=${PIPESTATUS[0]}
    cp native/dlss5-feed-host.log "$OUT/raw/" 2>/dev/null || true
else
    "$PYTHON" "${PYTEST_ARGS[@]}"
    STATUS=$?
fi

# --- Wine/NGX environment: CONFIGURE it, then snapshot it --------------------
# Deliberately not --check. The point of this step is to leave the prefix in a
# state where the gate below can pass; running only the diagnosis is exactly
# what let a missing DXVK dxgi.dll go unnoticed for a whole round, with the
# gate reporting 0xBAD00002 and nothing saying the setup had never been applied.
if [ "$WANT_M0" = "1" ] && [ "$WANT_REPORT" = "1" ]; then
    if [ -x tools/wine_ngx_setup.sh ]; then
        echo ""
        echo "=============================================================="
        echo " Wine NGX setup (APPLYING, then snapshotting)"
        echo "=============================================================="
        tools/wine_ngx_setup.sh 2>&1 | tee "$OUT/raw/wine_ngx_setup.txt"
        echo ""
        echo "--- after setup: the prefix as it now stands ---"
        tools/wine_ngx_setup.sh --check 2>&1 | tee "$OUT/raw/wine_ngx_environment.txt"
    fi
fi

# --- M0 gate, run separately so its log is captured verbatim ----------------
if [ "$WANT_M0" = "1" ] && [ "$WANT_REPORT" = "1" ]; then
    if [ -x tools/m0_env_gate.sh ]; then
        echo ""
        echo "=============================================================="
        echo " M0 environment gate (worker --test under Wine)"
        echo "=============================================================="
        tools/m0_env_gate.sh --out "$OUT/raw" 2>&1 | tee "$OUT/raw/m0_gate.txt"
    fi
fi

# --- summary ----------------------------------------------------------------
SUMMARY="$OUT/report.md"
if [ "$WANT_REPORT" = "1" ]; then
    {
        echo "# NeuralScreen MVP — test report"
        echo ""
        echo "- **run:** $STAMP (UTC)"
        echo "- **git:** $(git rev-parse --short HEAD 2>/dev/null) on $(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
        echo "- **python:** $("$PYTHON" --version 2>&1)"
        echo "- **pytest exit:** $STATUS $([ "$STATUS" = "0" ] && echo '(all passed)' || echo '(FAILURES — see raw/pytest.txt)')"
        echo "- **M0 gate:** $([ "$WANT_M0" = "1" ] && echo 'included' || echo 'not run (pass --m0)')"
        echo ""
        echo "## Summary line"
        echo ""
        echo '```'
        grep -E '^(=+ )?[0-9]+ (passed|failed)|passed|failed|error' "$OUT/raw/pytest.txt" 2>/dev/null | tail -3 || echo "(no summary captured)"
        echo '```'
        echo ""
        echo "## Artifacts"
        echo ""
        echo "| file | what |"
        echo "|---|---|"
        echo "| \`raw/pytest.txt\` | full pytest output |"
        echo "| \`raw/environment.txt\` | GPU, driver, Wine, Vulkan, session |"
        [ -f "$OUT/raw/wine_ngx_setup.txt" ] && echo "| \`raw/wine_ngx_setup.txt\` | what the NGX/DXVK setup applied |"
        [ -f "$OUT/raw/wine_ngx_environment.txt" ] && echo "| \`raw/wine_ngx_environment.txt\` | the prefix after setup |"
        [ -f "$OUT/raw/m0_gate.txt" ] && echo "| \`raw/m0_gate.txt\` | M0 gate output |"
        [ -f "$OUT/raw/dlss5-feed-host.log" ] && echo "| \`raw/dlss5-feed-host.log\` | the worker's own log |"
        echo ""
        echo "## What to do with this"
        echo ""
        echo "Commit and push \`$OUT/\` — it is read directly from the repo."
    } > "$SUMMARY"
fi

echo ""
echo "=============================================================="
if [ "$STATUS" = "0" ]; then
    echo " RESULT: PASS"
else
    echo " RESULT: FAIL (exit $STATUS)"
fi
if [ "$WANT_REPORT" = "1" ]; then
    echo " report: $OUT/report.md"
    echo " push it:  git add $OUT && git commit -m 'test results $STAMP' && git push"
fi
echo "=============================================================="
exit "$STATUS"