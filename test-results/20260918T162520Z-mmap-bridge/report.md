# mmap bridge test — 20260918T162520Z

**RESULT: PASS — a native process and a Wine process share these pages in both directions.**

## Transport

```
  14.7 MB written and returned in 9.66ms mean over 10 rounds (3052 MB/s both ways)
  of which 2.75ms is our own write (5364 MB/s one way)
  for scale: a pipe read measured ~1100 MB/s on the analysis box,
```

## How to read it

- Ran `experiments/mmap_bridge/run.sh` on the box that has Wine.
- Each side fills the payload with its own byte and verifies *every* byte
  the other wrote, so a pass is a coherence claim, not a liveness check.
- Wine's `map_file_into_view` maps a writable file-backed view with
  `mmap(fd, MAP_SHARED)` — the same page cache native Linux uses — so a
  pass is the expected result, and a failure arrives named by Wine's own
  error strings rather than as a silent private copy.
- `--flush` was off: an msync per round forces writeback and overstated an
  earlier round trip by 4x.

Full output, including which process was on the other side:
`raw/bridge_check.log`.
