"""The GPU probe must separate contention from presence, and never guess.

A skewed timing run is expensive to notice after the fact (two 1440p runs of the same config read
29.1 and 35.3 ms an hour apart). A game holding 5.6 GiB at 7% utilisation does not slow a frame -
it takes no compute time - but it can wake up mid-run, so it is a warning rather than a stop. A
card at a low clock is neither: clocks drop when nothing runs. The bar itself is the machine's
(25% here, raised from 15% so a browser held open as a live capture source is not called
contention), and it is settable from the command line so the runner can take it from the policy.
"""
import json

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


def test_a_foreign_process_at_low_utilisation_is_a_warning(monkeypatch):
    """Holding memory is not the same as taking compute time."""
    with_smi(monkeypatch, "6", apps="9001, python3, 9000")
    state, why = gs.verdict(gs.nvidia_smi())
    assert state == "WARN"
    assert any("python3" in w for w in why)


def test_high_utilisation_makes_it_busy(monkeypatch):
    with_smi(monkeypatch, "72")
    state, why = gs.verdict(gs.nvidia_smi())
    assert state == "BUSY"
    assert any("utilization" in w for w in why)


def test_a_clocked_down_card_is_not_by_itself_busy(monkeypatch):
    """Clocks drop when nothing runs; that is idling, not contamination."""
    with_smi(monkeypatch, "0")
    gpu = gs.nvidia_smi()
    gpu["clock_sm_mhz"] = 400.0
    state, why = gs.verdict(gpu)
    assert state == "IDLE", why


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


def test_require_idle_refuses_a_resident_game(monkeypatch):
    steam = (r"4176838, S:\steamapps\common\Dying Light The Beast\ph_ft\work\bin\x64"
             r"\DyingLightGame_TheBeast_x64_rwdi.exe, 5670")
    with_smi(monkeypatch, "7", apps=steam)
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


def test_a_resident_game_is_a_warning_not_a_stop(monkeypatch):
    """5.6 GiB held at 7% util does not take compute time - but it can wake up mid-run."""
    steam = (r"4176838, S:\steamapps\common\Dying Light The Beast\ph_ft\work\bin\x64"
             r"\DyingLightGame_TheBeast_x64_rwdi.exe, 5670")
    with_smi(monkeypatch, "7", apps=steam)
    gpu = gs.nvidia_smi()
    assert gpu["compute_apps"][0]["name"] == "DyingLightGame_TheBeast_x64_rwdi.exe"
    state, why = gs.verdict(gpu)
    assert state == "WARN", why
    assert any("resident" in w for w in why)


def test_a_browser_between_the_old_bar_and_the_new_one_is_a_warning(monkeypatch):
    """The reason the bar moved: a browser playing video is the source, not a contender.

    At the old 15% this read BUSY, which refused exactly the runs that need a live window on
    screen - the closest thing to a GeForce Now stream this box can be pointed at. At 25% it reads
    WARN, so the run happens, and the report records how close to the bar it sat.
    """
    with_smi(monkeypatch, "18", apps="9001, chromium, 9000")
    assert gs.verdict(gs.nvidia_smi(), 15)[0] == "BUSY", "the old bar would have refused this run"
    state, why = gs.verdict(gs.nvidia_smi())
    assert state == "WARN", why
    assert any("chromium" in w for w in why)


def test_the_bar_can_be_moved_without_editing_the_file(monkeypatch):
    with_smi(monkeypatch, "18", apps="9001, chromium, 9000")
    assert gs.verdict(gs.nvidia_smi(), 10)[0] == "BUSY"
    assert gs.verdict(gs.nvidia_smi(), 25)[0] == "WARN"


def test_the_flag_sets_the_bar_and_the_json_reports_it(monkeypatch, capsys):
    with_smi(monkeypatch, "18")
    monkeypatch.setattr(gs.sys, "argv", ["gpu_status.py", "--json", "--busy-util", "10"])
    assert gs.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "BUSY"
    assert payload["busy_util"] == 10.0
