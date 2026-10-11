#!/usr/bin/env bash
# Put this port into a checkout of OpenDLSS-NR, idempotently, and stamp it.
#
#   experiments/opendlss_port/apply_to_port.sh /home/paul/dev/OpenDLSS-NR
#   (cd /home/paul/dev/OpenDLSS-NR && bash scripts/build_linux.sh)
#
# Why this exists as a script rather than two commands to type: the patch ADDS files,
# and `git apply` refuses when one of them is already in the working directory —
#
#     error: src/serve.cpp: already exists in working directory
#
# — after which the build script was not there to run (`bash: scripts/build_linux.sh:
# No such file or directory`) and the pipeline went on to run the *previous* binary
# while the console said nothing about it. The hand-written step listed one file to
# remove and missed the others. This derives the list from the patch itself, so it
# cannot miss one, and it writes the patch's own commit into the checkout so a run can
# say which patch its binary was built from.
set -euo pipefail

port="${1:?usage: apply_to_port.sh <OpenDLSS-NR checkout> [patch]}"
patch="${2:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/linux-port.patch}"

[ -d "$port/.git" ] || { echo "not a git checkout: $port" >&2; exit 2; }
[ -f "$patch" ] || { echo "no patch at $patch" >&2; exit 2; }

# The commit the patch was cut from. This is what a run has to be in sync with, so it is
# written into the checkout (build_linux.sh bakes it into the binary) rather than left to
# whoever remembers which patch they applied.
patch_id="$(sed -n 's/^From \([0-9a-f]\{40\}\) .*/\1/p' "$patch" | head -1)"
[ -n "$patch_id" ] || { echo "no 'From <sha>' header in $patch — is it a git format-patch?" >&2; exit 2; }

# Every path the patch creates, taken from the patch: a file git apply will not overwrite.
added="$(awk '/^diff --git /{line=$0; sub(/^.* b\//, "", line); f=line} /^new file mode/{print f}' "$patch")"

echo "port:   $port ($(git -C "$port" rev-parse --short HEAD))"
echo "patch:  $patch"
echo "commit: ${patch_id:0:12}"

# Drop the previous patch's edits to tracked files, then the files it added.
git -C "$port" checkout -- . 2>/dev/null || true
for path in $added; do
  [ -e "$port/$path" ] || continue
  rm -f "$port/$path"
  echo "removed $path (added by the patch, not tracked here)"
done

git -C "$port" apply --check "$patch" || {
  echo "the patch does not apply to this checkout." >&2
  echo "A checkout with unrelated changes in the files it touches is the usual reason;" >&2
  echo "'git -C $port status --short' shows what is in the way." >&2
  exit 1
}
git -C "$port" apply "$patch"
echo "$patch_id" > "$port/.ns-patch-id"

changed="$(git -C "$port" status --porcelain | wc -l | tr -d ' ')"
echo "applied: $changed file(s) changed or added in $port"
echo "stamped: $port/.ns-patch-id holds ${patch_id:0:12} (the build bakes it in)"
echo "next:    (cd $port && bash scripts/build_linux.sh)   # then: build/dlss5vk stamp"