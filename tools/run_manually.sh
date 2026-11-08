#!/bin/bash
# run_manually.sh — run outstanding run requests by hand, with a display.
#
# WHY THIS EXISTS
#
# The auto-runner's unit (tools/neuralscreen-runner.service) sets
# SDL_VIDEODRIVER=dummy and carries no DISPLAY, because "a run must not need
# one": every unattended run is a fixture run that reaches no compositor. That
# is the right bound for the queue's normal work, and it is exactly what makes a
# live capture impossible there — the XDG portal hands out a screen-cast only
# after its dialog is clicked, and a unit with no display has nowhere to put it.
#
# runs/README.md says the same thing from the other end: "anything driving the
# real compositor stays a manual run." This script is that manual run. It does
# what the unit does — fetch, run whatever is outstanding, publish results to
# the results branch — without the sandbox that makes a display impossible.
#
# YOUR ROLE
#
#   1. Queue a request in runs/queue/ and push it to main (as usual).
#   2. Run this script from a terminal in your graphical session.
#   3. When the portal dialog appears, pick the window (or screen).
#   4. The script runs it, pushes the result to the results branch, and exits.
#
# Nothing else. The dialog click is the only thing the unit cannot do for you.
#
# WHAT IT TOUCHES
#
#   The runner's OWN clone at policy["worktree"] (/opt/neuralscreen/state/repo by
#   default), not your dev checkout. The policy at /opt/neuralscreen/policy.toml,
#   which decides what may run. The results branch. It does not write to
#   /etc, install packages, or touch the developer's tree — same rules as the unit.
#
# THE TIMER, AND WHY IT IS STOPPED
#
# The timer would otherwise tick in the middle of this run and race it for the
# same requests. The runner writes an "attempted" marker before it runs a
# request, so the race mostly degrades to "one of them skips" — but "mostly" is
# not a property worth relying on when the two runs have different environments.
# So the timer is stopped for the duration and restarted on exit, including on
# failure. If the timer is not installed, both calls are no-ops.
#
# INSTALL (once, on the box)
#
#   install -m 0755 tools/run_manually.sh /opt/neuralscreen/run_manually.sh
#
# Install it into /opt/neuralscreen, beside auto_runner.py and policy.toml, not
# into the repo's tools/ directory on the box. The repo checkout the runner uses
# is its own private clone at /opt/neuralscreen/state/repo, and prepare_checkout
# resets it to origin/main on every pass - so a script run from there disappears
# or changes under you. /opt/neuralscreen is the operational directory and is not
# touched by the runner's resets.
#
# USAGE
#
#   /opt/neuralscreen/run_manually.sh                    # policy at the default path
#   /opt/neuralscreen/run_manually.sh /path/to/policy.toml
#   /opt/neuralscreen/run_manually.sh --include-manual   # accepted, see below
#
# A request that needs the dialog prints its capture split when it finishes; the
# numbers and any artifacts land in runs/done/<id>/ on the results branch.
set -uo pipefail

usage() {
    cat >&2 <<'USAGE'
usage: run_manually.sh [policy.toml] [--include-manual]

  policy.toml        the runner's policy. Default /opt/neuralscreen/policy.toml.
  --include-manual   accepted and already implied: this script exists to run the requests the
                     unattended ticker skips for being manual. The flag is here because it is
                     the runner's flag and someone will reasonably type it - before this it was
                     read as the policy path, and the script answered "no policy at
                     --include-manual", which is true and useless.
  -h, --help         this text.
USAGE
}

# Arguments are parsed rather than taken positionally. The first-argument-is-the-policy form cost
# someone a confusing failure on 2026-11-08: `run_manually.sh --include-manual` asked for a policy
# at a path named "--include-manual", and the error named the flag as a missing file.
POLICY=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --include-manual) shift ;;          # implied; accepted so it cannot be read as a path
        -h|--help) usage; exit 0 ;;
        --) shift; break ;;
        -*) echo "unknown option: $1" >&2; usage; exit 2 ;;
        *)
            if [[ -z "$POLICY" ]]; then POLICY="$1"
            else echo "unexpected argument: $1" >&2; usage; exit 2
            fi
            shift ;;
    esac
done
[[ $# -gt 0 ]] && { echo "unexpected argument: $1" >&2; usage; exit 2; }
POLICY="${POLICY:-/opt/neuralscreen/policy.toml}"
RUNNER="${NEURALSCREEN_RUNNER:-/opt/neuralscreen/auto_runner.py}"

if [[ ! -f "$POLICY" ]]; then
    echo "no policy at $POLICY" >&2
    if [[ "$POLICY" == /opt/neuralscreen/policy.toml ]]; then
        echo "  the box keeps its policy outside the repo, so it is installed by hand:" >&2
        echo "    install -m 0644 tools/runner_policy.example.toml /opt/neuralscreen/policy.toml" >&2
        echo "  (run that from a checkout of this repo, then edit it - the entries decide what may run)" >&2
    else
        echo "  that path was given as the policy argument; omit it to use the default" >&2
    fi
    exit 1
fi
if [[ ! -f "$RUNNER" ]]; then
    echo "no runner at $RUNNER" >&2
    echo "  install tools/auto_runner.py as that path first" >&2
    exit 1
fi

# A display is the whole reason this script exists. If there is none, say so
# rather than let a portal handshake fail somewhere deeper with a worse message.
if [[ -z "${WAYLAND_DISPLAY:-}" && -z "${DISPLAY:-}" ]]; then
    echo "no WAYLAND_DISPLAY or DISPLAY in this shell" >&2
    echo "  run this from a terminal inside the graphical session" >&2
    exit 1
fi
echo "display: WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-(unset)} DISPLAY=${DISPLAY:-(unset)}"

# The unit's deploy key and its empty ssh config, so the push needs no prompt.
# An empty ssh_config under -F is what keeps ssh from reading /etc/ssh/ssh_config,
# which the sandbox refuses and which reads as a rejected key. Run outside the
# sandbox that matters less, but using the same key keeps the two paths identical.
export GIT_SSH_COMMAND="ssh -F /opt/neuralscreen/ssh_config -i /opt/neuralscreen/deploy_key -o IdentitiesOnly=yes -o BatchMode=yes -o UserKnownHostsFile=/opt/neuralscreen/state/known_hosts -o StrictHostKeyChecking=accept-new"
export GIT_TERMINAL_PROMPT=0

# Stop the timer so the unit does not race this run; restore it on any exit.
stopped_timer=0
if systemctl --user is-active --quiet neuralscreen-runner.timer 2>/dev/null; then
    systemctl --user stop neuralscreen-runner.timer 2>/dev/null && stopped_timer=1
fi
restore() {
    if [[ "$stopped_timer" == "1" ]]; then
        systemctl --user start neuralscreen-runner.timer 2>/dev/null || true
    fi
}
trap restore EXIT INT TERM

# --include-manual is the whole difference from the timer: requests marked
# "manual": true are skipped by the unattended ticker (they need someone at the
# screen for the portal dialog), and this script is the only thing that takes
# them. Without the flag this script would find "nothing to do" on exactly the
# requests it exists to run.
#
# Not exec: the trap has to survive the call so the timer comes back.
python3 "$RUNNER" --policy "$POLICY" --once --include-manual
exit_code=$?
echo "runner exited $exit_code"
exit "$exit_code"
