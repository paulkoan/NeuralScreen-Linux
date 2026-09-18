"""Keep draining the frame source so the producer is never throttled.

Measured on the box, 2560x1440, same pipeline both times:

    nothing else in the loop      grab  12.8-13.4ms = 75-78 fps
    inside the MVP's loop         grab  ~238ms      = ~4 fps

The portal is not slow. The loop reads a frame only after the worker has
finished the previous one, and a screencast whose client stops consuming stops
producing — the queue leaks, buffers are not recycled, and the pipe is 64KB
against a 14.7MB frame. So the producer and the consumer ping-pong with a full
pipeline latency in each cycle and the capture leg absorbs the whole round trip
as "waiting for the compositor".

Draining continuously keeps the producer running at its own rate and leaves the
newest frame waiting, so a frame costs the worker's time instead of the worker's
time plus a producer round trip. The cost is the drain itself: copying 14.7MB at
75fps is a busy core, which is why this is opt-in rather than the default.

Staleness is reported rather than hidden. Because old frames are dropped, what
the loop processes is the newest frame available at that moment — and the age of
that frame is the honest latency the capture adds.
"""

from __future__ import annotations

import threading
import time


class Prefetch:
    """Wrap a frame source and keep its newest frame ready.

    Same surface as the source it wraps — `resolution`, `grab`, `close` — so the
    pipeline cannot tell the difference, plus `stats` for what the drain saw.
    """

    #: A broken producer surfaces on the drain thread; the consumer sees it here
    #: rather than blocking forever.
    error: BaseException | None = None

    def __init__(self, source, log=print):
        self.source = source
        self.resolution = source.resolution
        self._log = log

        self._lock = threading.Lock()
        self._ready = threading.Condition(self._lock)
        self._latest = None
        self._stamp = 0.0          # when the newest frame arrived
        self._seq = 0
        self._stop = threading.Event()
        self._taken = 0
        self._dropped = 0
        # Age at the moment each frame was taken. The first version reported the
        # age of the newest frame when stats() was CALLED, which is the age at
        # the end of the run — it printed "1064.8ms old when used" for a frame
        # that was used a second earlier. Recorded per take instead.
        self._age_last = 0.0
        self._age_max = 0.0
        self._age_sum = 0.0
        # The split the portal reports does not apply here: the grab is a lock
        # and a reference, and the waiting has moved to the drain thread. Set to
        # None so a caller reports no split rather than a split of zeros.
        self.last_wait = None
        self.last_read = None

        self._thread = threading.Thread(target=self._drain, daemon=True,
                                        name="capture-prefetch")
        self._thread.start()

    # -- the drain ---------------------------------------------------------

    def _drain(self) -> None:
        while not self._stop.is_set():
            try:
                frame = self.source.grab()
            except BaseException as exc:      # noqa: BLE001 - handed to consumer
                self.error = exc
                with self._ready:
                    self._ready.notify_all()
                return
            with self._ready:
                if self._latest is not None:
                    self._dropped += 1
                self._latest = frame
                self._stamp = time.monotonic()
                self._seq += 1
                self._ready.notify_all()

    # -- the source surface ------------------------------------------------

    def grab(self, timeout: float = 60.0):
        """The newest frame. Blocks only until the first one arrives.

        A producer that died is re-raised here rather than left as a frozen
        frame the loop keeps processing: a stalled picture that looks like
        progress is worse than a stopped run.
        """
        deadline = time.monotonic() + timeout
        with self._ready:
            while self._latest is None and self.error is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(
                        "the frame source produced nothing for "
                        f"{timeout:.0f}s (prefetch drain is stuck)")
                self._ready.wait(timeout=remaining)
            if self.error is not None:
                raise self.error
            self._taken += 1
            age = time.monotonic() - self._stamp
            self._age_last = age
            self._age_sum += age
            if age > self._age_max:
                self._age_max = age
            return self._latest

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5.0)
        self.source.close()

    # -- what the drain saw ------------------------------------------------

    def stats(self) -> dict:
        """What the drain saw: frames dropped, and how stale the frames used were.

        The ages are recorded when a frame is TAKEN, not when this is called.
        Reporting the newest frame's age at call time was the first version's
        bug: it printed "1064.8ms old when used" for a frame that had been used
        a second earlier, which reads as a catastrophic staleness that was not
        there.

        The mean age is the latency the capture adds per frame. With old frames
        dropped it should stay near one frame time; if it does not, the drain
        thread is being starved — which is what happens when the worker and the
        drain compete for memory bandwidth.
        """
        with self._ready:
            return {
                "drained": self._seq,
                "taken": self._taken,
                "dropped": self._dropped,
                "age_mean": (self._age_sum / self._taken) if self._taken else None,
                "age_max": self._age_max if self._taken else None,
                "age_last": self._age_last if self._taken else None,
            }
