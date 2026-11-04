"""Every method the app calls on ``st.display`` must exist on the Linux Display.

The Windows-era app was written against a much larger Display than `display_linux.Display`
provides, and each missing method surfaced as a crash at startup - first `set_lang`, then the
next one. This test compares the two sides statically (AST for the class, regex for the call
sites), so a gap is reported as a list instead of being discovered one crash at a time.

It needs neither pysdl2 nor a display: it reads the source.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DISPLAY = REPO / "display_linux.py"
CALLERS = ("main_linux.py", "startup_linux.py", "commands.py", "pipeline_linux.py",
           "channels.py")


def _defined() -> set[str]:
    tree = ast.parse(DISPLAY.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Display")
    names = {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}
    for node in cls.body:
        if isinstance(node, ast.FunctionDef) and node.name == "__init__":
            for stmt in node.body:
                for child in ast.walk(stmt):
                    if isinstance(child, ast.Assign):
                        for target in child.targets:
                            if (isinstance(target, ast.Attribute)
                                    and isinstance(target.value, ast.Name)
                                    and target.value.id == "self"):
                                names.add(target.attr)
    return names


def _used() -> dict[str, set[str]]:
    used: dict[str, set[str]] = {}
    pattern = re.compile(r"\b(?:st\.)?display\.([A-Za-z_][A-Za-z0-9_]*)")
    for name in CALLERS:
        path = REPO / name
        if not path.is_file():
            continue
        for match in pattern.finditer(path.read_text()):
            used.setdefault(match.group(1), set()).add(name)
    return used


def test_the_app_only_calls_what_the_display_provides():
    missing = {name: files for name, files in _used().items() if name not in _defined()}
    assert not missing, (
        "the app calls these on st.display and display_linux.Display does not define them: "
        + ", ".join(f"{name} ({', '.join(sorted(files))})" for name, files in sorted(missing.items()))
    )


def test_the_surface_includes_the_things_that_crashed():
    """Named individually so a regression says which one went missing, not just 'some gap'."""
    defined = _defined()
    for name in ("set_lang", "alert", "menu", "screen", "get_hwnd", "resize",
                 "enter_switch_mode", "exit_switch_mode", "is_switch_active",
                 "draw_overlay", "draw_capture_overlay", "set_hud_only",
                 "set_menu_opaque", "set_menu_input", "set_excluded_from_capture",
                 "set_fullscreen_layer", "set_window_layer"):
        assert name in defined, f"Display.{name} is gone"


def test_every_xlib_call_declares_argtypes():
    """A pointer passed to a function without argtypes is truncated - the v1 segfault, twice.

    Static on purpose: it needs no display and no SDL, so it runs everywhere.
    """
    import re
    source = DISPLAY.read_text()
    used = set(re.findall(r"_XLIB\.(X[A-Za-z]+)", source))
    declared = set(re.findall(r"_XLIB\.(X[A-Za-z]+)\.argtypes\s*=", source))
    assert used, "no Xlib calls found - the regex or the module changed"
    missing = sorted(used - declared)
    assert not missing, (
        "these are called without argtypes, so their pointer arguments are truncated: "
        + ", ".join(missing))
