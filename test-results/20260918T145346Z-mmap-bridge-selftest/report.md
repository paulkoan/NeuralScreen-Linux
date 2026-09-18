# mmap bridge test — 20260918T145346Z

**RESULT: PASS — the handshake works end to end. This run did NOT involve Wine.**

**Not a box result.** This run used the Python stand-in for the
Windows side, not Wine. It proves the harness works end to end and
says nothing about page sharing across the Wine boundary.

## Transport

```
  1.0 MB written and returned in 3.61ms mean over 3 rounds (553 MB/s both ways)
  of which 0.74ms is our own write (1355 MB/s one way)
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
