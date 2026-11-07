"""The worker's closing line is printed on the EOF the client causes, and must be kept.

`Worker.stop()` closes stdin; the worker reads that EOF, prints its last line and
returns. The stderr drain thread used to break on the flag `stop()` set *before* the
close, so the line printed in response to the close was dropped before it reached
`worker.logs` — which is why `r2026-11-08-midslot-run` reports `worker exit 0` with no
closing line at all. The mock worker prints "EOF after N frames" on that same EOF, so
it is the stand-in for the port's counters line.
"""

from __future__ import annotations

from minimal.loop import DEFAULT_PARAMS
from minimal.worker import Worker


def _worker(mock_worker_cmd) -> Worker:
    return Worker(160, 96, 160, 96, DEFAULT_PARAMS, cmd=mock_worker_cmd)


def test_the_worker_s_closing_line_on_eof_is_kept(mock_worker_cmd):
    w = _worker(mock_worker_cmd)
    try:
        w.start()
        assert w.wait_for_alive(2.0), (
            "the mock worker exited immediately:\n  " + "\n  ".join(w.logs))
    finally:
        code = w.stop()

    assert code == 0, f"the worker exited {code}; logs:\n  " + "\n  ".join(w.logs)
    assert any("EOF after" in line for line in w.logs), (
        "the worker's line printed on EOF was dropped before it reached logs: "
        + repr(w.logs))


def test_a_line_printed_after_the_close_still_arrives(mock_worker_cmd):
    """The close is what triggers the line, so it cannot already be in `logs` when it happens.

    This proves the drain thread is still reading *after* stdin is closed — the exact
    window the old ordering lost.
    """
    w = _worker(mock_worker_cmd)
    try:
        w.start()
        assert w.wait_for_alive(2.0), "\n  ".join(w.logs)
        assert not any("EOF after" in line for line in w.logs), (
            "the closing line cannot be there before the EOF that causes it")
    finally:
        w.stop()

    assert any("EOF after" in line for line in w.logs), (
        "the closing line did not survive the close: " + repr(w.logs))
