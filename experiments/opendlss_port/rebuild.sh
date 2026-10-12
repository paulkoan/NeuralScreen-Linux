#!/usr/bin/env bash
# Apply the current patch to the staged port and rebuild it, so the worker on this
# machine always matches the patch id the runs report.
#
#   bash experiments/opendlss_port/rebuild.sh [port-dir] [patch]
#
# Default port-dir is the STAGED copy (/opt/neuralscreen/port), not the developer's
# dev tree: the runs execute under a sandbox that cannot read the home directory, and
# a run that silently rebuilt the tree someone is editing would be worse than useless.
# Pass a path to rebuild a checkout elsewhere.
#
# Why this exists: a port change is a patch plus a build, and doing that by hand is how
# r2026-10-11-g came back marked
#
#   OUT OF SYNC - the worker was built from patch ea90414e2b00, this checkout has
#   c2c4279a9623 ... the run below is not the code in this checkout
#
# — the run's numbers were from the previous binary. This does the two steps in order,
# and then asks the binary what it was built from and fails if that is not the patch it
# was just handed. The stamp is the point: the check is the rebuilt binary's own answer,
# not this script's opinion that the build looked fine.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
port="${1:-/opt/neuralscreen/port}"
patch="${2:-$here/linux-port.patch}"

[ -d "$port/.git" ] || { echo "not a git checkout: $port" >&2; exit 2; }
[ -f "$patch" ] || { echo "no patch at $patch" >&2; exit 2; }

patch_id="$(sed -n 's/^From \([0-9a-f]\{40\}\) .*/\1/p' "$patch" | head -1)"
[ -n "$patch_id" ] || { echo "no 'From <sha>' header in $patch" >&2; exit 2; }

echo "rebuild: $port <- $(basename "$patch") (${patch_id:0:12})"

# Idempotent apply; the script derives the files it may remove from the patch itself.
bash "$here/apply_to_port.sh" "$port" "$patch"

if [ ! -f "$port/scripts/build_linux.sh" ]; then
  echo "the patch did not put scripts/build_linux.sh in $port" >&2
  echo "refusing to continue: the next command would fail with 'No such file or directory'" >&2
  echo "and the old binary would be left in place looking current." >&2
  exit 3
fi

(cd "$port" && bash scripts/build_linux.sh)

bin="$port/build/dlss5vk"
[ -x "$bin" ] || { echo "the build produced no executable at $bin" >&2; exit 4; }

# Ask the binary, not the build log. `stamp` needs no device and no model.
stamp="$("$bin" stamp 2>&1 | head -1)"
echo "stamp:   $stamp"

built="$(printf '%s' "$stamp" | sed -n 's/.*patch \([0-9a-f]\{8,\}\).*/\1/p')"
if [ -z "$built" ]; then
  echo "the binary printed no patch id - the stamp is not reaching it" >&2
  exit 5
fi
case "$patch_id" in
  "$built"*) ;;
  *) echo "the rebuilt binary says patch $built; the patch applied was ${patch_id:0:12}." >&2
     echo "A run would be marked OUT OF SYNC. Look at build/shaders and build/ptx for a" >&2
     echo "partial build (the PTX emitter list stopping early was this, once)." >&2
     exit 5 ;;
esac

echo "rebuilt: $bin is patch $built, which is the patch applied - runs will be in sync"
