#!/bin/bash
# Install the Hermes-side loop scripts into the neuralscreen profile.
#
#   hermes/install.sh            copy them in (safe to re-run; says what it did)
#   hermes/install.sh --check    report drift and change nothing (exit 1 if anything differs)
#
# These live in the repo so they can be read, diffed and restored; the profile directory is not a
# git repository, so this copy-in is the one manual step. Run it after editing anything here.
#
# The job definitions are deliberately not here. Schedules, prompts and the tick's own
# instructions live in the profile's cron/jobs.json and are owned by the scheduler; editing that
# file behind its back is how a job ends up disagreeing with the thing that runs it.
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
profile="${NEURALSCREEN_PROFILE:-/opt/data/profiles/neuralscreen}"
dest="$profile/scripts"
mode="${1:-install}"

if [ ! -d "$dest" ]; then
    echo "no scripts directory at $dest" >&2
    echo "  if this profile lives elsewhere, set NEURALSCREEN_PROFILE" >&2
    exit 1
fi

files="ns-progress-watchdog.sh ns-results-monitor.sh ns-cron-failure.py ns-tick-state.py ns-box-state.py"

case "$mode" in
    --check)
        drift=0
        for f in $files; do
            if [ ! -f "$dest/$f" ]; then
                printf '%-28s MISSING from %s\n' "$f" "$dest"
                drift=1
            elif ! cmp -s "$here/$f" "$dest/$f"; then
                printf '%-28s DIFFERS - the profile is not running this copy\n' "$f"
                drift=1
            else
                printf '%-28s in step\n' "$f"
            fi
        done
        if [ "$drift" -eq 0 ]; then
            exit 0
        fi
        echo "" >&2
        echo "The profile is running a different loop from the one this repo holds." >&2
        echo "Run hermes/install.sh to bring it into step." >&2
        exit 1
        ;;
    install)
        for f in $files; do
            if [ -f "$dest/$f" ] && cmp -s "$here/$f" "$dest/$f"; then
                printf '%-28s already in step\n' "$f"
                continue
            fi
            if install -m 0755 "$here/$f" "$dest/$f"; then
                printf '%-28s installed\n' "$f"
            else
                printf '%-28s FAILED to install\n' "$f" >&2
                exit 1
            fi
        done
        echo ""
        echo "The scheduler picks the scripts up on its next fire; there is nothing to restart."
        ;;
    *)
        echo "usage: install.sh [--check]" >&2
        exit 2
        ;;
esac
