"""The object the run is built on must not be given away to a temporary.

`minimal/__main__.py` prints its summary from the same `main()` that built the Pipeline, and the
reporting block rebound `pipe` to the capture pipe's byte count:

    if "capture_wait" in t:
        pipe = t.get("capture_pipe_bytes")        # the Pipeline is gone from here on
        ...
    if pipe.gpu is not None:                      # AttributeError: 'int' has no 'gpu'

The run that exposed it did 3152 frames and printed every number, then died on the way out: the
exit status said failure and the GPU line never appeared.

No run of the synthetic source could have caught it — the rebinding needs `capture_wait` in the
timings, which only the portal path reports. So this is a static check, not a run.

The rule generalises past the one name: inside `main()`, the name holding the Pipeline is assigned
once, and to the Pipeline.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parent.parent / "minimal" / "__main__.py"

_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


def _targets_of(node: ast.AST) -> list[ast.AST]:
    if isinstance(node, ast.Assign):
        return list(node.targets)
    if isinstance(node, (ast.AugAssign, ast.AnnAssign)):
        return [node.target]
    return []


def _assigned_names(node: ast.AST) -> list[str]:
    """Names bound inside `node`, not descending into nested scopes.

    A nested def's `pipe` is a different variable, and counting it would make the check above
    fire on innocent code — which is how a test like this gets deleted.
    """
    out: list[str] = []

    def visit(current: ast.AST) -> None:
        for child in ast.iter_child_nodes(current):
            if isinstance(child, _SCOPES):
                continue
            for target in _targets_of(child):
                if isinstance(target, ast.Name):
                    out.append(target.id)
                elif isinstance(target, (ast.Tuple, ast.List)):
                    out.extend(t.id for t in target.elts if isinstance(t, ast.Name))
            visit(child)

    visit(node)
    return out


def _main_function(tree: ast.AST) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            return node
    pytest.fail("no main() in minimal/__main__.py")


def _pipeline_name(main: ast.FunctionDef) -> str:
    """The name bound to `Pipeline(...)`: what the summary reporting must leave alone."""
    for child in ast.walk(main):
        if isinstance(child, ast.Assign) and isinstance(child.value, ast.Call):
            func = child.value.func
            if (isinstance(func, ast.Name) and func.id == "Pipeline"
                    and len(child.targets) == 1 and isinstance(child.targets[0], ast.Name)):
                return child.targets[0].id
    pytest.fail("no `x = Pipeline(...)` in main() — has the construction moved?")
    raise AssertionError  # unreachable; satisfies the declared return type


def test_the_pipeline_name_is_assigned_only_once_in_main():
    main = _main_function(ast.parse(SOURCE.read_text(encoding="utf-8")))
    name = _pipeline_name(main)
    hits = [n for n in _assigned_names(main) if n == name]
    assert hits == [name], (
        f"`{name}` is assigned {len(hits)} times in main(); the summary reporting must not reuse "
        f"the pipeline's name, or an otherwise successful run dies on its way out")


def test_the_walker_stops_at_a_scope_boundary():
    """If this fails the check above is worthless: it would count a nested def's own names."""
    tree = ast.parse(
        "def main():\n"
        "    pipe = Pipeline()\n"
        "    if True:\n"
        "        pipe = 3\n"
        "    def inner():\n"
        "        pipe = 4\n"
        "    return pipe\n")
    main = _main_function(tree)
    assert [n for n in _assigned_names(main) if n == "pipe"] == ["pipe", "pipe"]


def test_the_walker_finds_assignments_inside_branches_and_tuples():
    """The rebinding that caused this was one level inside an `if`."""
    tree = ast.parse(
        "def main():\n"
        "    a, b = 1, 2\n"
        "    try:\n"
        "        a = 3\n"
        "    except Exception:\n"
        "        a += 1\n"
        "    return a\n")
    main = _main_function(tree)
    names = _assigned_names(main)
    assert names.count("a") == 3 and "b" in names
