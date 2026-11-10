"""The reviewed copy of the box's policy, kept here so it can be read and diffed.

The policy lives outside the repository on purpose - it is what decides what may run, so a commit
must not be able to grant itself the machine - and that made it invisible from here: on 2026-11-10
three runs were spent establishing that an entry set `NS_WORKER_CMD` where `NEURALSCREEN_MODEL_DIR`
was wanted, because the only view of the file was a handful of env KEY names printed in a run report.

This file is the reviewed copy. The deployed one is the one that counts, and installing this over it
is a deliberate act:

    install -m 0644 /opt/neuralscreen/state/repo/ops/policy.toml /opt/neuralscreen/policy.toml

Every run also publishes what it actually ran under, as `runs/done/<id>/policy.toml` on the results
branch, so the two can always be diffed.

What these tests guard is the class of fault rather than the instance. A duplicated entry name is
silent: the runner keys entries in a dict, the last block wins, and the earlier one is dead text that
looks live. Two entries meant to differ that do not is the same silence one step further on.
"""
from __future__ import annotations

import tomllib
from pathlib import Path

POLICY = Path(__file__).resolve().parents[1] / "ops" / "policy.toml"
# The only two env names tools/port_profile.sh reads. Anything else is accepted by the policy editor
# and ignored by the program, which is exactly how a run measures the wrong model and looks fine.
PROFILER_ENV = ("NEURALSCREEN_MODEL_DIR", "NEURALSCREEN_PORT_BIN")


def entries() -> list[dict]:
    return tomllib.loads(POLICY.read_text())["entry"]


def test_every_entry_name_is_unique():
    names = [entry["name"] for entry in entries()]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    assert not duplicates, (
        f"{duplicates} appears more than once: the runner keys entries by name, so the last block "
        "wins and the earlier one is dead text that looks live")


def test_an_entry_that_profiles_sets_the_name_the_profiler_reads():
    for entry in entries():
        if not entry["name"].startswith("port-profile"):
            continue
        env = entry.get("env") or {}
        assert any(name in env for name in PROFILER_ENV), (
            f"{entry['name']} sets {sorted(env) or 'no env'} - tools/port_profile.sh reads only "
            f"{' and '.join(PROFILER_ENV)}, so this entry would profile the default model")


def test_the_two_profile_entries_measure_different_models():
    models = {entry["name"]: (entry.get("env") or {}).get("NEURALSCREEN_MODEL_DIR")
              for entry in entries() if entry["name"].startswith("port-profile")}
    assert models == {"port-profile": "/opt/neuralscreen/model",
                      "port-profile-small": "/opt/neuralscreen/model-small"}, models


def test_an_entry_named_for_the_small_network_names_the_small_model():
    for entry in entries():
        if "small" not in entry["name"] or entry["name"] == "model-small-extract":
            continue
        env = entry.get("env") or {}
        named = env.get("NEURALSCREEN_MODEL_DIR") or env.get("NS_WORKER_CMD") or ""
        assert "model-small" in named, f"{entry['name']} does not name the small model: {env}"


def test_the_small_network_pair_differs_only_in_the_model():
    """The fps and parity pair is an A/B, so the wrapper must not differ along with the model.

    `minimal-small` was defined twice and the `xvfb-run` copy won - so the only small-network entry
    the runner could use wrapped the client in a virtual X server while `minimal`, its comparison,
    did not. That pair would differ by two things at once, which is not a measurement, and it left a
    tick with nothing it was allowed to queue.
    """
    by_name = {entry["name"]: entry for entry in entries()}
    assert by_name["minimal-small"]["argv"] == by_name["minimal"]["argv"], (
        "the pair differs by more than the model: "
        f"{by_name['minimal']['argv']} against {by_name['minimal-small']['argv']}")
