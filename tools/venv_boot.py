"""Re-exec a tool into the repo's virtualenv when this interpreter cannot cope.

Not a command — it is imported by the tools next to it, which is why it is named
in NOT_COMMANDS in tests/test_tool_scripts.py.

Why it is needed: these tools are documented as `tools/<name> ...`, so the
shebang decides which interpreter runs. With the venv not activated that is the
system python, which has neither numpy nor cv2 nor jeepney, and the tool dies
with a traceback instead of doing its job — on the GPU box, where a round trip
is expensive. The shell tools here already prefer `$REPO/.venv/bin/python`; this
is the same rule for the Python ones.

Used as the very first thing a tool does:

    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from venv_boot import reexec_into_repo_venv
    reexec_into_repo_venv(__file__, modules=("numpy", "jeepney"))

    # everything else, including the third-party imports, comes after this

Two details that are easy to get wrong, and both were:

  * The check compares `sys.prefix`, not `sys.executable`. A venv's `bin/python`
    is normally a symlink to the system interpreter, so resolving both paths
    makes them compare equal and the guard silently never fires.
  * `os.execv` replaces the process, so a guard variable is set first. Without
    it, a venv that is also missing the dependency would loop forever instead of
    reaching the code that reports the problem.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_GUARD = "NSL_VENV_REEXEC"


def reexec_into_repo_venv(script: str, *, modules: tuple[str, ...] = ("numpy",)) -> None:
    """Replace this process with the repo venv's interpreter, if it is needed.

    Returns normally when the current interpreter is already good enough, so the
    caller can simply carry on.
    """
    if os.environ.get(_GUARD) == "1":
        return

    repo = Path(script).resolve().parent.parent
    venv = repo / ".venv"
    venv_python = venv / "bin" / "python"

    if not venv_python.exists():
        return                      # nothing better to switch to
    if Path(sys.prefix).resolve() == venv.resolve():
        return                      # already running in it

    for name in modules:
        try:
            __import__(name)
        except ImportError:
            break
    else:
        return                      # it can do the job as it is

    os.environ[_GUARD] = "1"
    os.execv(str(venv_python),
             [str(venv_python), str(Path(script).resolve()), *sys.argv[1:]])
