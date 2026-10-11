# What to run next

A queue of *planned* requests, in order. The point of it is that the thinking step - deciding
what to measure next and why - is written down somewhere reviewable, instead of living only in
a chat. A cron agent tick may take the first item, turn it into a request in `runs/queue/`, and
delete it from here. Nothing else in this file is executable, and one item per tick is the
limit: a loop that queues its own follow-ups without a written plan is a loop nobody reviews.

## 1. Is the pass helping, on video rather than desktop chrome?

The fixture is a whole-desktop capture, so the pass runs over browser chrome, a sidebar and
thumbnails - fine for timing, useless for judging quality. This run asks for a crop of the
video area only, and saves both frames, so a comparison is between two pictures of the same
thing and nothing else.

* id: `r2026-10-11-d`
* entry: `minimal`
* args: `--source image --input-image fixtures/video-crop.png --headless --frames 60
  --worker-log --shm --no-motion --send-ahead 2 --save-before before.png --save-after after.png`
* artifacts: `before.png`, `after.png`
* needs first: `fixtures/video-crop.png`, a 1280x720-or-larger crop of the video region from
  `fixtures/youtube-1440p.png`. Until it exists this item should not be queued.

## 2. Where the worker's 22ms actually goes

`serve` reports `network+composite` 12.5ms and `proxy` 4-5ms per frame; the pass alone measured
9.96ms in `bench`. The gap is the composite and the proxy expansion sharing a queue with the
network. A run at 720p work size would separate "cost that scales with pixels" from "cost that
does not", and the `serve frame` lines already carry the split.

* id: `r2026-10-11-e`
* entry: `minimal`
* args: `--source image --input-image fixtures/youtube-1440p.png --headless --size 1280x720
  --frames 60 --worker-log --shm --no-motion --send-ahead 2`
* artifacts: none

## 3. The missing temporal history

Everything so far is a single-frame NR: the client sends a zero motion field and `serve`
keeps no history, so the network never sees a previous frame. This is the difference between
what we have and what the network is for, and it is not a request to queue yet - it needs
`serve` to keep a history feature and the client to send real motion vectors, which is a
conversation, not a run.
