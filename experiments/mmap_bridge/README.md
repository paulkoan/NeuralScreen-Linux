# The shared-file bridge test

One question: **can a native Linux process and a Wine process see each other's
writes to the same memory-mapped file?**

It matters because the DLSS worker is a prebuilt Windows binary whose only input
paths are a stdin pipe and a Windows *named section*. Named sections are not
reachable from a native Linux process — that is what blocked shared memory in the
MVP — and it is the whole reason a 2560x1440 frame costs ~85ms even with NGX
switched off. A file, though, might be reachable: Wine maps `/` as `Z:\`, so both
sides can map the same file, and two `MAP_SHARED` mappings of one file are the
same physical pages.

If this fails, the own-host pathway is dead and nothing downstream of it is worth
building. If it works, the frame can stop travelling through pipes.

## Running it

```bash
sudo pacman -S mingw-w64-gcc      # Arch; Debian: gcc-mingw-w64-x86-64
cd experiments/mmap_bridge
./run.sh                          # builds and runs against real Wine
```

The first run will open a Wine prefix. Fifteen seconds or so is normal.

`./run.sh --selftest` runs the identical handshake with `fake_windows.py` standing
in for the Windows side. That covers the layout and the protocol and says
**nothing** about page sharing — it is there so that a failure under Wine is
about Wine rather than about the handshake, and so CI can cover the protocol with
no Wine installed at all.

## Reading the result

```
 RESULT: PASS — a native process and a Wine process share these pages in both
 directions.
```

Each side fills the payload with its own byte — the native side `0xA5`, the
Windows side `0x5A` — and each verifies *every* byte of what the other wrote. One
byte that neither side wrote means the pages are not shared, so `PASS` is a real
claim rather than a liveness check. `--bytes` defaults to 14745600, exactly one
2560x1440 RGBA frame, so the throughput is directly comparable to the MVP's pipe
numbers.

Measured on the analysis box with the Python stand-in (14.7MB, no flush):

```
  14.7 MB written and returned in 27.0ms mean  (1093 MB/s both ways)
  of which 6.24ms is our own write             (2362 MB/s one way)
```

against **~1100 MB/s** for a pipe read on the same box, so roughly **2x** the
transport. The Wine half is the number that matters and it is not measured yet.

## Two things that were wrong first time

Both were caught by running it, which is why it is worth running.

**`--flush` is off by default.** Coherence does not need an `msync`: two shared
mappings of one file are the same physical pages, and flushing only forces
writeback. The first version flushed every round and reported 113ms for a 14.7MB
round trip — 4x the truth — because it was mostly measuring disk. The flag stays
so the cost can be measured rather than assumed; a real implementation must not
pay it per frame.

**The pass/fail line says what actually ran.** With `--windows-cmd` the Windows
side is not Wine, so the result says so and the Wine claim is explicitly marked
unproven. An earlier version announced "a native process and a Wine process share
these pages" regardless.

## What a PASS would and would not mean

A PASS with real Wine means the *transport* is available. It does not mean the
worker can use it: the worker's input paths are still a pipe and a named section,
so using a file-backed mapping means **writing our own host** — the same job,
with a transport we choose, reusing the NGX plumbing from
`native/dlss5-feed-host64.cpp`. That is Phase B, and it is a build rather than an
experiment.