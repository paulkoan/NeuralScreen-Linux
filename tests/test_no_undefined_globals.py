"""No name is used before anything defines it.

The v1 startup found these one crash at a time: `COMMAND_MAP` imported from a module that never
had it, `Display` used in `pipeline_linux.rebuild_pipeline` without an import, `UI_STRINGS` used
one line above its own import, and three `capture_linux` helpers used in `settings_io` that were
never imported at all. Each was a NameError or ImportError waiting for the first run that reached
it.

`symtable` answers this without importing anything: a symbol that is global in some scope and
assigned or imported nowhere at module level is a name the interpreter will fail to resolve.
"""
from __future__ import annotations

import builtins
import symtable
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
BUILTINS = set(dir(builtins))

# Supplied by the interpreter/import system rather than assigned in the module.
INJECTED = {"__file__", "__name__", "__doc__", "__builtins__", "__spec__", "__loader__",
            "__package__"}


def _module_names(table: symtable.SymbolTable) -> set[str]:
    names = set()
    for symbol in table.get_symbols():
        if symbol.is_assigned() or symbol.is_imported() or symbol.is_namespace():
            names.add(symbol.get_name())
    return names


def _undefined(table, module_names, scope=(), out=None):
    out = [] if out is None else out
    for symbol in table.get_symbols():
        name = symbol.get_name()
        if (symbol.is_global() and not symbol.is_assigned() and not symbol.is_imported()
                and name not in module_names and name not in BUILTINS and name not in INJECTED):
            out.append(("/".join(scope) or "<module>", name))
    for child in table.get_children():
        _undefined(child, module_names, scope + (child.get_name(),), out)
    return out


def _modules():
    return sorted(p for p in REPO.glob("*.py") if p.name != "pipeline.py")


@pytest.mark.parametrize("path", _modules(), ids=lambda p: p.name)
def test_every_global_is_defined_somewhere(path):
    table = symtable.symtable(path.read_text(), str(path), "exec")
    missing = _undefined(table, _module_names(table))
    assert not missing, (
        f"{path.name}: these names are used as globals and defined nowhere - "
        + ", ".join(f"{name} (in {scope})" for scope, name in missing)
    )


def _module_surface(name: str) -> set[str]:
    """Public names a module offers, following `from X import *` the way the interpreter does."""
    path = REPO / f"{name}.py"
    tree = symtable.symtable(path.read_text(), str(path), "exec")
    names = _module_names(tree)
    # A star import re-exports the other module's public names; resolve it, since a caller
    # cannot see through it either.
    import ast as _ast
    for node in _ast.walk(_ast.parse(path.read_text())):
        if isinstance(node, _ast.ImportFrom) and any(a.name == "*" for a in node.names):
            if node.module and (REPO / f"{node.module}.py").is_file():
                names |= {n for n in _module_surface(node.module) if not n.startswith("_")}
    return names


def test_module_attributes_the_app_calls_exist():
    """`pipeline_linux.follow_monitor` was missing while every import looked fine.

    Imports are checked above; this checks the attributes reached through a module object.
    """
    import ast as _ast

    modules = {p.stem for p in REPO.glob("*.py")}
    callers = ["main_linux.py", "startup_linux.py", "commands.py", "channels.py"]
    surfaces = {}

    missing = []
    for caller in callers:
        path = REPO / caller
        if not path.is_file():
            continue
        tree = _ast.parse(path.read_text())
        # names that are local variables anywhere in the file (a local named `display` is a
        # window, not the module)
        local_vars = {n.id for n in _ast.walk(tree)
                      if isinstance(n, _ast.Name) and isinstance(n.ctx, _ast.Store)}
        for node in _ast.walk(tree):
            if not (isinstance(node, _ast.Attribute) and isinstance(node.value, _ast.Name)):
                continue
            module = node.value.id
            if module not in modules or module == path.stem or module in local_vars:
                continue
            if module not in surfaces:
                surfaces[module] = _module_surface(module)
            if node.attr not in surfaces[module]:
                missing.append(f"{caller}:{node.lineno} {module}.{node.attr}")

    assert not missing, "these are called on a module that does not define them: " + "; ".join(
        sorted(set(missing)))
