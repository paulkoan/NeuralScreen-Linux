# minimal/ — the MVP pipeline

One loop: **capture a frame → run it through the DLSS5 neural pass → put the
result on screen.** Nothing else. See [../docs/MVP-PLAN.md](../docs/MVP-PLAN.md)
for the milestones and the reasoning.

```
python -m minimal                       # fullscreen, until the window is closed
python -m minimal --frames 120          # bounded run
python -m minimal --windowed            # draw in a window
python -m minimal --headless --frames 3 --save-after out.png
python -m minimal --list-monitors
```

Esc or `q` while the window has focus quits.

## What runs

| file | does |
|---|---|
| `capture.py` | X11 screen capture via `mss`, returns `(H, W, 4)` uint8 **RGBA** |
| `worker.py` | launches `native/run_worker.sh` (`wine nvngx.dll --live`), sends frames, reads results |
| `display.py` | SDL2 window with a streaming texture |
| `loop.py` | wires the three together; `Pipeline`, `run()` |
| `__main__.py` | the CLI above |

`protocol.py` at the repo root owns the wire format and is shared with the
Windows-derived modules. Its struct layouts are checked against the C++
`static_assert`s in `tests/test_protocol_sizes.py`.

## Deliberate limits, and why

- **Pipe transport, not shared memory.** `protocol.SharedFrameBuffer` calls
  `mmap.mmap(-1, size, tagname=...)`; `tagname` is a Windows-only keyword and
  raises `TypeError` on Linux. On top of that, Wine's `OpenFileMappingA`
  namespace is not POSIX shm, so a Python-created mapping would not be visible
  to the worker anyway. The pipe path (colour and motion inline) is real and
  works today; shared memory is a later optimisation.
- **Zero motion vectors.** NGX wants a motion field. Zeros mean "nothing moved",
  which is correct for a static desktop and enough to prove the pass runs. Real
  optical flow is `guides.py`'s job and a later milestone.
- **X11 only.** PipeWire/Wayland capture is a later milestone. `mss` works on
  X11 and on XWayland.
- **No UI.** No menu, HUD, hotkeys, recording, window mode or tray.

## Overriding the worker for tests

`NS_WORKER_CMD` replaces the launcher command, which is how the tests run the
whole pipeline against `tests/mock_worker.py` with no GPU and no Wine:

```bash
NS_WORKER_CMD="python tests/mock_worker.py" python -m minimal --frames 3 --headless
```