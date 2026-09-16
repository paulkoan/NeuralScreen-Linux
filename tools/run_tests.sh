#!/bin/bash
# run_tests.sh — run the MVP test suite, optionally write and push a report.
#
#   tools/run_tests.sh                          # run the tests, print the summary
#   tools/run_tests.sh --report                 # also write test-results/<timestamp>/
#   tools/run_tests.sh --report --m0            # include the M0 environment gate
#   tools/run_tests.sh --report --m0 --m1       # and the live-pipeline gate
#   tools/run_tests.sh --report --m0 --m1 --push  # and push the report
#
# --m0 runs the synthetic worker self-test. --m1 runs the actual MVP end to end
# (python -m minimal) and measures whether the pass changed the frame. They are
# not the same APIs — see the header of tools/m1_pipeline_gate.sh.
#
# The report directory carries the human summary plus every raw log, so results
# travel as files instead of pasted text. See docs/MVP-PLAN.md.
#
# --push uses whatever git credentials are already configured for this repo;
# GIT_ASKPASS is honoured if you export it.

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

PYTHON="${PYTHON:-$REPO/.venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
    PYTHON="$(command -v python3)"
fi

# The venv is managed by uv from pyproject.toml + uv.lock, so a missing pytest
# means the venv is out of sync — not that pytest needs installing on its own.
# And this must never suggest plain `pip install`: that puts one package into
# whatever interpreter is active and leaves the rest of the venv stale, which is
# how a checkout ends up missing pysdl2 while its owner believes it is complete.
if ! "$PYTHON" -c "import pytest" >/dev/null 2>&1; then
    echo "pytest is not installed for $PYTHON — the venv is out of sync."
    if command -v uv >/dev/null 2>&1 && [ -f uv.lock ]; then
        echo "  syncing:  uv sync"
        UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uvcache}" \
            uv sync >/dev/null 2>&1 || true
    fi
    # uv sync targets ./.venv; if $PYTHON points somewhere else, install into it
    # directly rather than silently leaving the wrong interpreter without pytest.
    if ! "$PYTHON" -c "import pytest" >/dev/null 2>&1 && command -v uv >/dev/null 2>&1; then
        UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uvcache}" \
            uv pip install --python "$PYTHON" pytest >/dev/null 2>&1 || true
    fi
    if ! "$PYTHON" -c "import pytest" >/dev/null 2>&1; then
        echo ""
        echo "Could not install pytest. The project's venv is managed by uv;"
        echo "from the repo root run:"
        echo ""
        echo "    uv sync"
        echo ""
        echo "That creates .venv from uv.lock and installs every declared"
        echo "dependency, so it also fixes anything else that is missing."
        echo ""
        echo "Without it the test suite cannot run at all."
        exit 3
    fi
    echo "pytest installed."
    echo ""
fi

WANT_REPORT=0
WANT_M0=0
WANT_M1=0
WANT_PUSH=0
for arg in "$@"; do
    case "$arg" in
        --report) WANT_REPORT=1 ;;
        --m0)     WANT_M0=1 ;;
        --m1)     WANT_M1=1; WANT_REPORT=1 ;;
        --push)   WANT_PUSH=1; WANT_REPORT=1 ;;
        -h|--help)
            sed -n '2,18p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
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
# Two variants per round, because each round-trip costs a manual run on the GPU
# box. `direct` is the default path: create goes through nvngx_dlssnr.dll's own
# export, evaluate through the SDK helper's Core entry point. `via-core` sends
# both through NGX Core. If direct yields 0xBAD00004 FAIL_FeatureNotFound and
# via-core passes, the handle is being registered with one runtime and evaluated
# by the other, and the fix belongs in the worker rather than in the environment.
if [ "$WANT_M0" = "1" ] && [ "$WANT_REPORT" = "1" ]; then
    if [ -x tools/m0_env_gate.sh ]; then
        echo ""
        echo "=============================================================="
        echo " M0 environment gate (worker --test under Wine)"
        echo "=============================================================="
        tools/m0_env_gate.sh --out "$OUT/raw" 2>&1 | tee "$OUT/raw/m0_gate.txt"
        M0_RC=${PIPESTATUS[0]}
        echo "     direct exit: $M0_RC (0=pass 1=fail 2=blocked)"
        # The copy in the pytest block above runs BEFORE this gate, so the log it
        # checks for is from the previous run or absent. Copy again here, or the
        # report lists dlss5-feed-host.log as an artifact it never carries.
        cp -f native/dlss5-feed-host.log "$OUT/raw/" 2>/dev/null || true

        echo ""
        echo "=============================================================="
        echo " M0 environment gate — variant: NS_NGX_VIA_CORE=1"
        echo "=============================================================="
        mkdir -p "$OUT/raw/via-core"
        tools/m0_env_gate.sh --out "$OUT/raw/via-core" --via-core 2>&1 \
            | tee "$OUT/raw/m0_gate_via_core.txt"
        VIA_RC=${PIPESTATUS[0]}
        echo "     via-core exit: $VIA_RC (0=pass 1=fail 2=blocked)"
        cp -f native/dlss5-feed-host.log "$OUT/raw/via-core/" 2>/dev/null || true
    fi
fi

# --- M1 gate: the live path, end to end -------------------------------------
# Separate from M0 because it is a different set of calls. M0's --test creates
# feature 18 through the NR runtime and then evaluates it through NGX Core's
# entry point, which fails with 0xBAD00004 FAIL_FeatureNotFound. The real
# pipeline (EvaluateVideo, reached by `wine nvngx.dll --live`) uses the NR
# runtime for both. This gate therefore runs the MVP and asks the only question
# that matters for the deliverable: did the frame come out of the pass changed?
if [ "$WANT_M1" = "1" ] && [ "$WANT_REPORT" = "1" ]; then
    if [ -x tools/m1_pipeline_gate.sh ]; then
        echo ""
        echo "=============================================================="
        echo " M1 — live pipeline gate (MVP end to end)"
        echo "=============================================================="
        mkdir -p "$OUT/raw/m1"
        tools/m1_pipeline_gate.sh --out "$OUT/raw/m1" 2>&1 \
            | tee "$OUT/raw/m1_gate.txt"
        M1_RC=${PIPESTATUS[0]}
        echo "     m1 exit: $M1_RC (0=pass 1=fail 2=blocked)"
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
        [ -f "$OUT/raw/m0_gate.txt" ] && echo "| \`raw/m0_gate.txt\` | M0 gate output (direct path) |"
        [ -f "$OUT/raw/m0_gate_via_core.txt" ] && echo "| \`raw/m0_gate_via_core.txt\` | M0 gate output with NS_NGX_VIA_CORE=1 |"
        [ -f "$OUT/raw/via-core/dlss5-feed-host.log" ] && echo "| \`raw/via-core/\` | same artifacts for the via-core variant |"
        [ -f "$OUT/raw/m1_gate.txt" ] && echo "| \`raw/m1_gate.txt\` | M1 gate: both variants |"
        [ -f "$OUT/raw/m1/pass/before.png" ] && echo "| \`raw/m1/pass/\` | NR pass on a known test card |"
        [ -f "$OUT/raw/m1/baseline/before.png" ] && echo "| \`raw/m1/baseline/\` | control: same input, effect dialled to zero |"
        [ -f "$OUT/raw/m1/capture/before.png" ] && echo "| \`raw/m1/capture/\` | the same on the real screen — the deciding artifact |"
        [ -f "$OUT/raw/m1/pass/analysis.txt" ] && echo "| \`raw/m1/*/analysis.txt\` | how much the pass changed each frame |"
        [ -f "$OUT/raw/dlss5-feed-host.log" ] && echo "| \`raw/dlss5-feed-host.log\` | the worker's own log |"
        echo ""
        echo "## What to do with this"
        echo ""
        echo "Commit and push \`$OUT/\` — it is read directly from the repo."
    } > "$SUMMARY"
fi

# --- auto-push the results --------------------------------------------------
# Opt-in. Commits only the report directory, never anything else that happens to
# be dirty in the tree, and leaves the commit local if the push fails so nothing
# is lost.
PUSH_STATUS="not requested"
if [ "$WANT_PUSH" = "1" ] && [ "$WANT_REPORT" = "1" ]; then
    echo ""
    echo "--- pushing results ---"

    if ! git rev-parse --git-dir >/dev/null 2>&1; then
        PUSH_STATUS="skipped: not a git repository"
    elif [ -z "$(git remote 2>/dev/null)" ]; then
        PUSH_STATUS="skipped: no git remote configured"
    else
        BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
        [ -z "$BRANCH" ] || [ "$BRANCH" = "HEAD" ] && BRANCH="main"

        git add -- "$OUT" 2>/dev/null || true
        if git diff --cached --quiet -- "$OUT" 2>/dev/null; then
            PUSH_STATUS="nothing new to commit"
        else
            if git commit -q -m "test results $STAMP" -- "$OUT" 2>/dev/null; then
                echo "  committed: test results $STAMP"
                PUSH_OUT="$(git push origin "$BRANCH" 2>&1)"
                PUSH_RC=$?
                echo "$PUSH_OUT" | sed 's/^/  /'
                if [ "$PUSH_RC" = "0" ]; then
                    PUSH_STATUS="pushed to origin/$BRANCH"
                else
                    # The commit is safe locally; do not pretend otherwise.
                    PUSH_STATUS="push FAILED — commit is local, push it by hand"
                fi
            else
                PUSH_STATUS="commit failed (is user.name/user.email set?)"
            fi
        fi
    fi
    echo "  -> $PUSH_STATUS"
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
    if [ "$WANT_PUSH" = "1" ]; then
        echo " push:   $PUSH_STATUS"
    else
        echo " push it:  git add $OUT && git commit -m 'test results $STAMP' && git push"
        echo "           (or pass --push next time)"
    fi
fi
echo "=============================================================="
exit "$STATUS"