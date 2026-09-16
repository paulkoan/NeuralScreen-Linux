"""One place for "a declared dependency is missing" messages.

These used to each say `pip install <name>`, which sent someone to install a
single package into whatever interpreter happened to be active — and then the
next missing one, and the next. The venv here is managed by uv from
`pyproject.toml` and `uv.lock`; when something is absent the whole venv is out of
date, and one command fixes all of it.

Keeping the text in one function stops the four call sites from drifting apart,
which is how the versions of this message would otherwise end up disagreeing.
"""

from __future__ import annotations

#: The one command that makes a checkout runnable.
UV_SYNC = "uv sync --extra test"


def hint(dist: str, module: str) -> str:
    """A message that names the missing package *and* the way out.

    `module` is the import name, which is often not the distribution name —
    pysdl2 imports as `sdl2`, opencv-python as `cv2` — and saying which one was
    missing saves the reader working it out.
    """
    return (
        f"{dist} is not installed (no module named {module!r}).\n"
        f"  This project's venv is managed by uv. From the repo root:\n"
        f"    {UV_SYNC}\n"
        f"  That creates .venv from uv.lock and installs every declared "
        f"dependency, so it fixes this and anything else that is also missing."
    )