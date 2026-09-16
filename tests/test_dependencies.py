"""Every dependency the project declares must actually be importable.

This exists because a checkout failed at runtime with

    startup failed: pysdl2 is not installed (pip install pysdl2)

for a package that `pyproject.toml` had listed all along. The venv was simply out
of sync, and nothing checked — so it was found by running the program on the
machine where iterating is expensive, instead of by the test suite, which runs in
seconds and on any machine.

The gap is worth naming: the suite imported `minimal.*`, and the modules that
need an optional dependency guard their import with try/except so the rest of the
package still works. That is right for the library and wrong for a health check —
it makes a missing dependency invisible until the exact feature is used.

So this asserts the environment rather than trusting it. One test asserts each
declared dependency imports; another asserts this file knows about all of them,
so adding a dependency to pyproject.toml cannot silently skip the check.
"""

from __future__ import annotations

import importlib
import re
import sys
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# The distribution name and the module it provides are often different, and the
# mismatch is exactly what makes "is it installed?" awkward to answer by hand.
DIST_TO_MODULE = {
    "numpy": "numpy",
    "opencv-python": "cv2",
    "pygame": "pygame",
    "av": "av",
    "mss": "mss",
    "pysdl2": "sdl2",
    "jeepney": "jeepney",
}

TEST_EXTRA_TO_MODULE = {
    "pytest": "pytest",
}


def _pyproject() -> dict:
    with (REPO / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)


def _names(entries: list[str]) -> list[str]:
    """Strip version specifiers and markers: 'numpy>=1.24' -> 'numpy'."""
    return [re.split(r"[<>=!~\[; ]", e.strip(), maxsplit=1)[0] for e in entries]


def _declared() -> list[str]:
    return _names(_pyproject()["project"]["dependencies"])


def _declared_dev() -> list[str]:
    """The dev dependency group (PEP 735) — installed by `uv sync` by default.

    A group rather than an optional-dependency extra on purpose: with an extra,
    pytest is absent unless every command remembers `--extra test`, and the
    failure that produces looks like a broken project rather than a missing flag.
    """
    groups = _pyproject().get("dependency-groups", {})
    return _names(groups.get("dev", []))


def test_the_pyproject_lists_some_dependencies():
    """A guard so a moved or renamed key cannot make the checks below vacuous."""
    assert _declared(), "no dependencies parsed out of pyproject.toml"
    assert "pysdl2" in _declared(), (
        "pysdl2 is the dependency whose absence prompted this test")


@pytest.mark.parametrize("dist", _declared() + _declared_dev())
def test_declared_dependency_is_installed(dist):
    """Each declared dependency must import in the interpreter running the tests."""
    module = {**DIST_TO_MODULE, **TEST_EXTRA_TO_MODULE}.get(dist)
    assert module is not None, (
        f"{dist} is declared in pyproject.toml but this test does not know which "
        f"module it provides. Add it to DIST_TO_MODULE in {Path(__file__).name}.")
    try:
        importlib.import_module(module)
    except ImportError as exc:
        from minimal.deps import UV_SYNC
        pytest.fail(
            f"{dist} is declared in pyproject.toml but `import {module}` failed: {exc}\n"
            f"  The venv is out of sync with the project. Recreate it with:\n"
            f"    {UV_SYNC}")


def test_the_expectation_map_covers_every_declared_dependency():
    """Adding a dependency must force a decision here, not skip the check."""
    known = set(DIST_TO_MODULE) | set(TEST_EXTRA_TO_MODULE)
    declared = set(_declared()) | set(_declared_dev())
    unknown = sorted(declared - known)
    assert not unknown, (
        f"declared but not covered: {unknown}\n"
        f"  add them to DIST_TO_MODULE in {Path(__file__).name} so they are checked, "
        f"otherwise a missing one goes unnoticed until runtime")


def test_the_modules_the_mvp_imports_at_startup_are_available():
    """The imports `python -m minimal` needs before it can do anything.

    Kept separate from the per-distribution check because this is the user-facing
    symptom: which failure they actually see when they start the program.
    """
    for module in ("numpy", "cv2", "pygame", "av", "sdl2"):
        importlib.import_module(module)