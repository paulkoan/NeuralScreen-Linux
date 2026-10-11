# Run requests, and the results they come back as

The loop: a request is committed to `main`, `tools/auto_runner.py` on the GPU box picks it
up, runs it inside a sandbox, and commits what happened to the `results` branch. Nobody has
to be at the keyboard, and nothing about what may run is decided by the commit that asks.

```
  main                                  GPU box                        results
  ────                                  ───────                        ───────
  runs/queue/<id>.json  ──fetch──▶  policy check ──▶ sandbox ──▶  runs/done/<id>/
                                                                   ├── request.json
                                                                   ├── command.txt
                                                                   ├── result.json
                                                                   ├── report.md
                                                                   ├── stdout.log / stderr.log
                                                                   └── <artifacts>
```

## Asking for a run

Write `runs/queue/<id>.json` and commit it. The id is the directory the result lands in, so
it is also the thing that stops a request running twice.

```json
{
  "id": "r2026-10-12-a",
  "entry": "minimal",
  "args": ["--input-image", "fixtures/youtube-1440p.png", "--headless",
           "--frames", "60", "--worker-log", "--shm", "--no-motion", "--send-ahead", "2"],
  "timeout_s": 300,
  "artifacts": ["before.png", "after.png"],
  "note": "does the loop now sit under 60ms?"
}
```

* `entry` must be one the policy names. Anything else is refused, recorded and pushed —
  a request nobody ran and nobody noticed is the failure mode worth engineering against.
* `args` are passed to `execve` as they are. There is no shell anywhere in the path, so
  `$(...)`, `;` and backticks are strings and nothing else.
* `artifacts` are copied out of the run into the result directory. They must be relative
  paths inside the checkout.

## Reading a result

`runs/done/<id>/report.md` has the command, the exit code, how long it took and the tail of
both streams. `result.json` has the same as data. Exit codes the runner itself uses: `126`
refused, `125` the runner failed, `124` killed by the timeout — anything else is the program
talking.

The `results` branch is a snapshot of the tree the run happened on, plus `runs/done/`. So a
result can always be read next to the exact code that produced it. Only the runner writes
that branch; requests come from `main`.

## What this cannot do

Live capture. The portal hands out a screen-cast only after someone clicks the dialog, so
anything driving the real compositor stays a manual run. That is why the fixture exists:
`--input-image` plus `--headless` exercises everything except the capture path and the
display stage, with no session involved. Those two, and the question of whether the picture
is actually *right*, are what the manual runs are for.

## Stopping it

```sh
touch /opt/neuralscreen/PAUSE                  # nothing runs; the timer keeps ticking
rm /opt/neuralscreen/PAUSE
systemctl --user status neuralscreen-runner.service
journalctl --user -u neuralscreen-runner.service -n 50
```

Installation - a systemd user unit, no root, nothing in /etc - is the header of
`tools/neuralscreen-runner.service`, and what may run at all is
`tools/runner_policy.example.toml`.
