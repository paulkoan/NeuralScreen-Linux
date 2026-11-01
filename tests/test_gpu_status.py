"""The GPU probe must say BUSY for a shared card and UNKNOWN when it cannot tell.

A skewed timing run is expensive to notice after the fact (two 1440p runs of the same config read
29.1 and 35.3 ms an hour apart), so the probe has to fail loudly rather than quietly report a
comfortable number. Parsing is pinned against the real nvidia-smi CSV shape.
"""
import tools.gpu_status as gs


def fake_run(util="3", apps=""):
    """Stand in for nvidia-smi: the main query, and the compute-app list."""
    def _run(cmd, timeout=15):
        if "--query-compute-apps" in " ".join(cmd):
            return apps
        if util is None:
            return ""
        return (f"NVIDIA GeForce RTX 4080 SUPER, GPU-abc, {util}, 621, 16376, "
                f"2610, 2610, 42, 62.4, 320.0, P8")
    return _run


def with_smi(monkeypatch, util="3", apps=""):
    """nvidia-smi is present and answers; the sandbox has no such binary, so both are faked."""
    monkeypatch.setattr(gs.shutil, "which", lambda name: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(gs, "run", fake_run(util, apps))


def test_parses_the_nvidia_csv(monkeypatch):
    with_smi(monkeypatch, "3")
    gpu = gs.nvidia_smi()
    assert gpu["name"] == "NVIDIA GeForce RTX 4080 SUPER"
    assert gpu["util_percent"] == 3.0
    assert gpu["mem_total_mib"] == 16376.0
    assert gpu["clock_max_sm_mhz"] == 2610.0
    assert gpu["compute_apps"] == []


def test_an_idle_card_is_idle(monkeypatch):
    with_smi(monkeypatch, "4")
    state, why = gs.verdict(gs.nvidia_smi())
    assert state == "IDLE", why


def test_a_desktop_process_holding_vram_is_not_a_contender(monkeypatch):
    with_smi(monkeypatch, "6", apps="812, Xwayland, 220")
    state, why = gs.verdict(gs.nvidia_smi())
    assert state == "IDLE", why


def test_a_foreign_compute_process_makes_it_busy(monkeypatch):
    with_smi(monkeypatch, "6", apps="9001, python3, 9000")
    state, why = gs.verdict(gs.nvidia_smi())
    assert state == "BUSY"
    assert any("python3" in w for w in why)


def test_high_utilisation_makes_it_busy(monkeypatch):
    with_smi(monkeypatch, "72")
    state, why = gs.verdict(gs.nvidia_smi())
    assert state == "BUSY"
    assert any("utilization" in w for w in why)


def test_a_clocked_down_card_is_busy(monkeypatch):
    """0% utilisation at half the SM clock means someone else has the power budget."""
    with_smi(monkeypatch, "0")
    gpu = gs.nvidia_smi()
    gpu["clock_sm_mhz"] = 400.0
    state, why = gs.verdict(gpu)
    assert state == "BUSY", why


def test_no_smi_at_all_is_unknown_not_idle(monkeypatch):
    monkeypatch.setattr(gs.shutil, "which", lambda name: None)
    monkeypatch.setattr(gs, "run", fake_run(None))
    state, why = gs.verdict(gs.nvidia_smi())
    assert state == "UNKNOWN"
    assert why


def test_require_idle_exits_nonzero_when_busy(monkeypatch):
    with_smi(monkeypatch, "72")
    monkeypatch.setattr(gs.sys, "argv", ["gpu_status.py", "--require-idle"])
    assert gs.main() == 1


def test_require_idle_is_silent_when_idle(monkeypatch):
    with_smi(monkeypatch, "2")
    monkeypatch.setattr(gs.sys, "argv", ["gpu_status.py", "--require-idle"])
    assert gs.main() == 0


def test_process_names_are_shortened_to_something_readable():
    """nvidia-smi hands back whole command lines, megabytes of switches and Windows paths."""
    long_line = ("/usr/lib/chromium/chromium --type=gpu-process --ozone-platform=wayland "
                 "--gpu-preferences=YAAAAAAAAAAgAQAEAAAAAAAAAAAAAGAASAAAAAAAAAABAAAAAAAAAEAA")
    assert gs.short_name(long_line) == "chromium"
    steam = (r"S:\steamapps\common\Dying Light The Beast\ph_ft\work\bin\x64"
             r"\DyingLightGame_TheBeast_x64_rwdi.exe")
    assert gs.short_name(steam) == "DyingLightGame_TheBeast_x64_rwdi.exe"
    assert gs.short_name("") == "(unreadable command line)"


def test_a_resident_game_makes_the_card_busy(monkeypatch):
    """A game holding VRAM at 0% utilisation is still contamination: it moves the clocks."""
    steam = (r"4176838, S:\steamapps\common\Dying Light The Beast\ph_ft\work\bin\x64"
             r"\DyingLightGame_TheBeast_x64_rwdi.exe, 5670")
    with_smi(monkeypatch, "7", apps=steam)
    gpu = gs.nvidia_smi()
    assert gpu["compute_apps"][0]["name"] == "DyingLightGame_TheBeast_x64_rwdi.exe"
    state, why = gs.verdict(gpu)
    assert state == "BUSY"
    assert any("DyingLightGame" in w for w in why)
