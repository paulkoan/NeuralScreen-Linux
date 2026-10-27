# Capture split and resolution — 2026-10-27 window captures

Source of truth: results branch of `/opt/data/neuralscreen-linux`, runs under `runs/done/`.
Extracted by task `t_18c802a2` for the final report on the HUMAN GFN card `t_a17e544e`.

## The line the pipeline prints

From `runs/done/r2026-10-27-c/stdout.log:23` (also quoted verbatim in that run's `report.md:32`):

```
capture split: wait 0.1ms  read 27.4ms   (read ~19ms at 2560x1440 means we are draining a stocked pipe; read far above that means the compositor was dribbling)
```

Raw numbers: `capture_wait = 0.0001 s` (0.1 ms), `capture_read = 0.0274 s` (27.4 ms).

Reading: the portal grab does not block (wait 0.1 ms — the buffer is already there), and the
read takes 27.4 ms against the pipeline's own ~19 ms baseline for a 2560x1440 frame. So the
compositor is dribbling ~8 ms per frame beyond a fully stocked pipe — mild, but it is the
compositor and not our read loop. This is consistent with the per-frame capture spread in the
same run: min 19.4 / median 27.3 / max 58.5 ms over 120 frames.

## Resolution

The capture was taken at **2560x1440**, and the work frame stayed at 2560x1440
(work scale 1.00, NGX ceiling 2560x1440).

Evidence, three independent places:

1. Run request/argv: `--size 2560x1440` (`runs/done/r2026-10-27-c/request.json`, `command.txt`).
2. Pipeline's own line (`stdout.log:14`):
   `source window  capture 2560x1440  ->  work 2560x1440 (work scale 1.00, NGX ceiling 2560x1440)`
3. The saved frames themselves — `gfn-before.png` and `gfn-after.png` are both 2560x1440
   (PNG IHDR: width 2560, height 1440; bytes 5,011,035 and 5,700,456; sha256 prefixes
   f2ddb3d94d105681 and c7ec7c4c959db6f0).

The gst pipeline confirms the same size: `video/x-raw,format=RGBA,width=2560,height=1440`.

## Which runs count

| run | source | exit | split line? | resolution | note |
|---|---|---|---|---|---|
| r2026-10-27-a | window | 2 | no | requested 2560x1440 | never started: `Permission denied` canonicalizing `/opt/neuralscreen/state/repo/.venv/bin/python` |
| r2026-10-27-b | window | 2 | no | requested 2560x1440 | same permission failure as a |
| r2026-10-27-c | window | 0 | **yes** | **2560x1440** | 120 frames, 14.208 s = 8.45 fps; portal handshake completed; this is the run to quote |
| r2026-10-27-d | image | 0 | no | 2560x1440 | static image source; the split line is only printed when `capture_wait` is timed, i.e. portal/window captures |

So the only real-session run that produced frames **and** a capture split is `r2026-10-27-c`.
Runs a and b failed before the pipeline started, so they carry no split numbers and should not
be cited as successful sessions.

## Other per-frame timings in the same run (for context)

`runs/done/r2026-10-27-c/stdout.log:18`:
`timing: capture 27.7ms  send 9.7ms  recv 65.8ms  display 12.6ms   (total 115.7ms/frame, 8.6 fps)`

Capture CPU: 9.99 s over 14.21 s = 70% of one core.
