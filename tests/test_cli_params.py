"""`--param NAME=VALUE` — the switch that makes a run reproducible and tunable.

Two reasons it exists, and both are worth a test:

  * **It is the control.** Dialling the effect to zero is the only way to tell
    how much of a before/after difference is the neural pass and how much is the
    frame making a round trip through Wine and back. Without it, "the pass
    changed the frame by 4.5/255" cannot be attributed.
  * **It is the tuning dial.** The first real-screen run showed the pass acting
    hardest on the 1.6% of pixels that are bright — text — so being able to turn
    those strengths down without editing code is the next thing anyone wants.

These run without a display: `--param` is validated before anything touches a
screen, so even the end-to-end checks here need no X server.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


# --- parsing ---------------------------------------------------------------

def test_no_overrides_gives_the_defaults():
    from minimal.__main__ import parse_params
    from minimal.loop import DEFAULT_PARAMS
    assert parse_params(None) == DEFAULT_PARAMS
    assert parse_params([]) == DEFAULT_PARAMS


def test_a_float_parameter_is_read_as_a_float():
    from minimal.__main__ import parse_params
    params = parse_params(["intensity=0"])
    assert params["intensity"] == 0.0
    assert isinstance(params["intensity"], float)


def test_an_integer_parameter_is_read_as_an_integer():
    from minimal.__main__ import parse_params
    params = parse_params(["profile=3"])
    assert params["profile"] == 3
    assert isinstance(params["profile"], int)


def test_overrides_apply_in_order_and_stack():
    from minimal.__main__ import parse_params
    params = parse_params(["intensity=0.5", "local_tone=0", "profile=2"])
    assert params["intensity"] == 0.5
    assert params["local_tone"] == 0.0
    assert params["profile"] == 2


def test_the_control_combination_is_expressible():
    """The exact flags the M1 gate's `baseline` variant passes."""
    from minimal.__main__ import parse_params
    params = parse_params(["intensity=0", "local_tone=0", "local_structure=0"])
    assert params["intensity"] == 0.0
    assert params["local_tone"] == 0.0
    assert params["local_structure"] == 0.0
    # and it left the others alone
    assert params["skin_structure"] == -1.0


def test_an_unknown_name_is_rejected_with_the_real_names():
    """A typo must fail here, not be silently dropped on the way to the worker."""
    from minimal.__main__ import parse_params
    with pytest.raises(ValueError) as exc:
        parse_params(["intesity=0"])          # note the typo
    message = str(exc.value)
    assert "intesity" in message
    assert "intensity" in message, "the message must list the names that do exist"


def test_a_missing_equals_is_rejected():
    from minimal.__main__ import parse_params
    with pytest.raises(ValueError, match="NAME=VALUE"):
        parse_params(["intensity"])


def test_a_non_numeric_value_is_rejected():
    from minimal.__main__ import parse_params
    with pytest.raises(ValueError):
        parse_params(["intensity=lots"])
    with pytest.raises(ValueError):
        parse_params(["profile=2.5"])


def test_parsing_does_not_mutate_the_defaults():
    """Otherwise one run's overrides would leak into the next."""
    from minimal.loop import DEFAULT_PARAMS
    from minimal.__main__ import parse_params
    before = dict(DEFAULT_PARAMS)
    parse_params(["intensity=0", "profile=9"])
    assert DEFAULT_PARAMS == before


# --- the CLI itself --------------------------------------------------------

def test_help_documents_the_flag_and_the_known_names():
    proc = subprocess.run([sys.executable, "-m", "minimal", "--help"],
                          cwd=REPO, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    assert "--param" in proc.stdout
    for name in ("intensity", "local_tone", "profile"):
        assert name in proc.stdout, f"{name} should be listed in --help"


def test_the_cli_fails_fast_on_a_bad_parameter():
    """And before it opens a screen, so this needs no display."""
    proc = subprocess.run([sys.executable, "-m", "minimal", "--param", "nope=1"],
                          cwd=REPO, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 2, f"expected exit 2, got {proc.returncode}"
    assert "bad --param" in proc.stderr
    assert "nope" in proc.stderr