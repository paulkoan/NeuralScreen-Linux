"""The shared-file bridge test (Phase A of the own-host pathway).

The Wine half cannot be tested here — this box has no Wine, no GPU and no
compositor — so what these cover is everything upstream of Wine: the layout the
two sides agree on, the handshake itself, and the two ways the first version
quietly lied about what it had measured.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

BRIDGE = Path(__file__).resolve().parent.parent / "experiments" / "mmap_bridge"
sys.path.insert(0, str(BRIDGE))

import bridge_check  # noqa: E402


def test_the_layout_header_parses_to_sane_values():
    """bridge_check.py reads its constants out of the C header rather than
    restating them. If the parser ever stops understanding that header the
    bridge would fail in a confusing way, so it is pinned here."""
    assert bridge_check.MAGIC == "NSBR"
    assert bridge_check.HDR >= 16, "the header must hold magic + state + round + len"
    assert bridge_check.PAYLOAD_OFF >= 16
    assert 0 < bridge_check.CAPACITY <= 64 * 1024 * 1024


def test_the_offsets_do_not_overlap():
    used = {
        "magic": bridge_check.MAGIC_OFF,
        "state": bridge_check.STATE_OFF,
        "round": bridge_check.ROUND_OFF,
        "len": bridge_check.LEN_OFF,
    }
    spans = sorted((off, off + 4, name) for name, off in used.items())
    for (start, end, name), (next_start, _, next_name) in zip(spans, spans[1:]):
        assert end <= next_start, f"{name} overlaps {next_name}"
        assert start >= 0
        assert end <= bridge_check.PAYLOAD_OFF, (
            f"{name} runs into the payload at {bridge_check.PAYLOAD_OFF}"
        )


def test_capacity_holds_a_1440p_frame():
    assert bridge_check.CAPACITY >= bridge_check.FRAME_1440P == 2560 * 1440 * 4


@pytest.fixture(scope="module")
def handshake(tmp_path_factory):
    """One real run of the handshake, with the Python stand-in for the Windows
    side. Small payload: this is about the protocol, not about throughput."""
    workdir = tmp_path_factory.mktemp("bridge")
    proc = subprocess.run(
        [sys.executable, str(BRIDGE / "bridge_check.py"),
         "--rounds", "2", "--bytes", "300000", "--dir", str(workdir),
         "--windows-cmd", f"{sys.executable} {BRIDGE / 'fake_windows.py'} {{path}}"],
        capture_output=True, text=True, timeout=120,
    )
    return proc


def test_the_handshake_passes_with_the_python_stand_in(handshake):
    assert handshake.returncode == 0, handshake.stdout + handshake.stderr
    assert "RESULT: PASS" in handshake.stdout
    # Both directions were verified byte by byte, not just "it answered".
    assert "0 with mismatches" in handshake.stdout


def test_the_result_does_not_claim_wine_when_wine_was_not_used(handshake):
    """The first version printed "a native process and a Wine process share
    these pages" even when --windows-cmd had swapped Wine for a Python stand-in.
    A pass that overstates what it proved is worse than no test."""
    assert "did NOT involve Wine" in handshake.stdout
    assert "NOT proven by this run" in handshake.stdout


def test_the_rates_are_labelled_in_mb_not_gb(handshake):
    """The first version divided bytes/1e6/second and called the result GB/s,
    overstating it a thousandfold."""
    assert "MB/s" in handshake.stdout
    assert "GB/s" not in handshake.stdout


def _unguarded(text: str, call: str, guard: str) -> list[str]:
    """Lines that call `call` without `guard` on the line above.

    Line-based on purpose: matching on a substring finds an indented call inside
    a guard and calls it unguarded, which is how this check first failed.
    """
    lines = text.splitlines()
    out = []
    for i, line in enumerate(lines):
        if call not in line:
            continue
        prev = lines[i - 1].strip() if i else ""
        if not prev.startswith(guard):
            out.append(line.strip())
    return out


def test_flushing_is_opt_in_on_both_sides():
    """A per-round flush forces writeback: it made a 14.7MB round trip look like
    113ms when the truth was 27ms. Both sides must keep it behind the flag, and
    this is the cheapest way to notice if that gets undone."""
    c = (BRIDGE / "bridge_win.c").read_text()
    assert "g_flush" in c
    unguarded = _unguarded(c, "FlushViewOfFile(", "if (g_flush)")
    assert not unguarded, f"unguarded flush in bridge_win.c: {unguarded}"

    py = (BRIDGE / "fake_windows.py").read_text()
    assert "do_flush" in py
    unguarded = _unguarded(py, "mm.flush()", "if do_flush:")
    assert not unguarded, (
        f"unguarded flush in the stand-in: {unguarded} — the two sides would pay "
        f"different costs"
    )


def test_the_runner_is_valid_bash():
    r = subprocess.run(["bash", "-n", str(BRIDGE / "run.sh")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_a_selftest_report_cannot_be_mistaken_for_a_box_result():
    """--push writes into test-results/, where a stand-in run would otherwise sit
    looking exactly like a result from the box that has Wine."""
    s = (BRIDGE / "run.sh").read_text()
    assert "-mmap-bridge-selftest" in s, "the selftest needs its own suffix"
    assert "Not a box result" in s, "and the report has to say so too"
    assert "--push" in s and "NS_GIT_ASKPASS" in s, (
        "the push must use the same auth convention as tools/run_tests.sh"
    )


def test_the_runner_is_executable():
    run = BRIDGE / "run.sh"
    assert run.is_file()
    assert run.stat().st_mode & 0o111, "run.sh needs its exec bit (and 100755 in git)"