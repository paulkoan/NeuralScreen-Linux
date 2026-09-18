#!/usr/bin/env bash
# The shared reporting tail for experiments that run on the GPU box.
#
# Both experiment runners write a report into test-results/ and push it, and both
# had their own copy of that. The auth dance is the part that must not drift: a
# push with no terminal fails as "wrong credentials", which reads like a GitHub
# problem and is not one, and each copy would eventually explain it differently.
#
# Sourced, not executed. Callers provide:
#   push_report <outdir> <commit-subject> [commit-body]
#
# Deliberately does not rely on the caller's `set -o pipefail` for the push
# status: `git push ... | sed` tests sed, not git, and that is a bug waiting for
# whoever removes pipefail from a caller.

push_report() {
    local out="$1" subject="$2" body="${3:-}"
    local repo askpass commit_ok push_out
    repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

    echo
    echo "report: $out/report.md"

    cd "$repo" || return 1

    # The convention tools/run_tests.sh already uses. There is no terminal here
    # for git to prompt on, so a credential helper that prompts cannot work.
    askpass="${NS_GIT_ASKPASS:-$HOME/.neuralscreen/github-askpass.sh}"
    if [ -x "$askpass" ]; then
        export GIT_ASKPASS="$askpass"
        export GIT_TERMINAL_PROMPT=0
        echo "  auth: GIT_ASKPASS=$askpass"
    else
        echo "  auth: no askpass script at $askpass. There is no terminal here, so"
        echo "        a prompting credential helper fails as 'wrong credentials'."
        echo "        Set NS_GIT_ASKPASS to a script that prints the token."
    fi

    if ! git add "$out"; then
        echo "  git add failed for $out" >&2
        return 1
    fi

    # `if` conditions are exempt from the callers' `set -e`, which matters: a
    # bare `var=$(failing command)` would abort the script before the status
    # could be read.
    if [ -n "$body" ]; then
        commit_ok=0
        git commit -q -m "$subject" -m "$body" || commit_ok=1
    else
        commit_ok=0
        git commit -q -m "$subject" || commit_ok=1
    fi
    if [ "$commit_ok" -ne 0 ]; then
        echo "  commit failed (is user.name/user.email set?)" >&2
        return 1
    fi
    echo "  committed: $subject"

    if push_out="$(git push origin HEAD 2>&1)"; then
        echo "$push_out" | sed 's/^/  /'
        echo "  pushed $(git rev-parse --short HEAD)"
    else
        echo "$push_out" | sed 's/^/  /'
        echo "  push FAILED — the commit is safe locally at $out, push it by hand" >&2
        return 1
    fi
    return 0
}
