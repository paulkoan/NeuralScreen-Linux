#!/bin/bash
# upload_stats.sh <repo> <log-path> <run-status>
#
# Commit one run's log and put it on main, then check that main actually has it.
#
# WHY THE CHECK
#
# The first version pushed and reported success from the push's exit code. It printed
# "stats: uploaded 20261106-223743.log" and the file was not on the remote: the systemd runner
# works in the same clone and does
#
#     git checkout -f -B main origin/main && git reset --hard origin/main
#
# every tick. Land that between the commit and the push and the commit is gone, so the push has
# nothing to send - which still exits 0. A success message that means "the command returned zero"
# is worse than no message, because it stops you looking.
#
# So: commit, push by SHA, then ask the remote what it has. Anything short of the remote naming
# our commit is reported as not uploaded, with the path to the log that is still local.
#
# Pushing by SHA is what makes the reset survivable: the runner moves refs, it does not delete
# objects, so a commit made a second earlier is still pushable after HEAD has been moved.
set -uo pipefail

REPO=${1:?usage: upload_stats.sh <repo> <log-path> [run-status]}
LOG=${2:?usage: upload_stats.sh <repo> <log-path> [run-status]}
STATUS=${3:-0}
REL=${LOG#"$REPO"/}
BRANCH=${STATS_BRANCH:-main}
ASKPASS=${GIT_ASKPASS:-/opt/data/secrets/github-askpass.sh}
export GIT_TERMINAL_PROMPT=0

say()  { echo "stats: $*"; }
warn() { echo "stats: $*" >&2; }

if ! git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1; then
    say "not a git repository at $REPO - the log is saved at $LOG and nowhere else"
    exit 0
fi

remote_head() {
    GIT_ASKPASS="$ASKPASS" git -C "$REPO" ls-remote origin "refs/heads/$BRANCH" 2>/dev/null \
        | head -1 | cut -f1
}

# Two attempts: the first can lose its commit to a runner tick, and re-staging recovers it.
for attempt in 1 2; do
    git -C "$REPO" add -- "$LOG" 2>/dev/null || { warn "could not stage $REL"; exit 0; }

    if git -C "$REPO" diff --cached --quiet; then
        # Already committed by an earlier attempt, or nothing changed. Either way the commit
        # to push is HEAD's, and the loop below decides whether it is really ours.
        :
    else
        git -C "$REPO" commit -q -m "stats: local run $(basename "$LOG" .log), exit $STATUS" \
            || { warn "commit failed"; exit 0; }
    fi

    SHA=$(git -C "$REPO" rev-parse HEAD 2>/dev/null)
    if [[ -z "$SHA" ]] || ! git -C "$REPO" cat-file -e "$SHA:$REL" 2>/dev/null; then
        # HEAD does not carry the log: the working tree was reset out from under us. Re-stage and
        # commit on the next pass rather than pushing a commit that cannot contain it.
        warn "HEAD ($SHA) does not contain $REL - the tree moved under us, retrying"
        continue
    fi

    if ! GIT_ASKPASS="$ASKPASS" git -C "$REPO" push -q origin "$SHA:refs/heads/$BRANCH" 2>/dev/null; then
        warn "push rejected (another writer got there first) - catching up"
        GIT_ASKPASS="$ASKPASS" git -C "$REPO" pull -q --rebase origin "$BRANCH" >/dev/null 2>&1 || true
        # If the rebase can still see our commit it keeps it on top and the next pass pushes the
        # new SHA; if the reset took it, the next pass commits it again.
        continue
    fi

    REMOTE=$(remote_head)
    if [[ "$REMOTE" == "$SHA" ]]; then
        say "uploaded $(basename "$LOG") ($SHA)"
        exit 0
    fi
    warn "the push reported success but origin/$BRANCH is ${REMOTE:-unknown}, not $SHA"
    continue
done

warn "NOT uploaded - the log is still at $LOG and its commit is $SHA in $REPO"
exit 0
