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
