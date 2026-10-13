# pipe_copy — what our copy out of the pipe costs

The capture leg is timed in two halves (`minimal/capture_wayland.py`):

```
capture split: wait 0.1ms  read 14.8ms
             the frame arriving   our copy of it
```

This experiment measures the second half on its own. A writer thread keeps an
`os.pipe` full of one frame; the reader drains it with the same `read1` loop the
capture uses and times itself. No compositor, no GStreamer, no Wine, no worker.

```bash
python3 experiments/pipe_copy/bench.py          # 9 rounds per size
python3 experiments/pipe_copy/bench.py 21       # more rounds
```

It prints best, median and every round per size, and MB/s, for 2560x1440,
1280x720 and 128x128.

## Why it exists

Two claims in `docs/M0-FINDINGS.md` rest on this number and neither had a script:

* round 14: "copying a 14.7MB frame out of a stocked pipe costs **13-19ms** here
  (1108 MB/s), which is ~11% of the 125ms grab";
* rounds 16-23: `read` is **9.9-15.3ms** in every split ever reported from the
  GPU box, and it is the half that never moves.

If the GPU box's `read` were to come back far above this bench, the bytes are
arriving slowly and the compositor is late — a different fault with a different
repair. If it matches, the pipe copy is at memory speed and the frame's own
arrival is the only remaining explanation for a large `wait`.

## Measured here

The analysis box (not the GPU box), 2026-10-13:

Two runs of 9 rounds each (the spread between rounds on this box is large, so
the median is the number to read and the best is not):

```
2560x1440   14.75 MB   median  10.17ms then 11.08ms   (every round 6.08-17.74ms)
1280x720     3.69 MB   median   2.85ms then  2.95ms   (every round 1.74-4.22ms)
128x128      0.07 MB   median   0.03ms then  0.03ms
```

~0.7ms per MB, 1250-1450 MB/s. Both the GPU box's splits (9.2-20.2ms at 1440p,
31 grabs over 17 runs) and round 14's 13-19ms sit inside this bench's band, and
it scales with the frame, so the copy is the pipe's and not the compositor's.

Note this is a *pipe* measurement: it says nothing about `pipewiresrc`'s own
copy out of KWin's buffer, or about `videoconvert`/`videoscale`, which are on
the producer side of the pipe and show up only in the run's `capture cpu:` line.
