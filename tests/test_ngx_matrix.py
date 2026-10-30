"""The matrix must name the stage that failed, not just "it failed".

Six gate runs produce six similar logs. The value of the table is that `create 0xBAD0000B` and
`evaluate 0xBAD00004` are different bugs; these fixtures pin both, plus a pass and a blocked
prerequisite run where the gate never reaches init.
"""
import importlib.util
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "tools" / "ngx_matrix.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("ngx_matrix", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PASS = """\
[host] NVSDK_NGX_D3D12_Init -> 0x00000001 (Success)
[arch] patch installed: 1 cards cached, architecture 0x190 (spoofed to the DLL's accepted value)
[pure] direct feature 18 ready: 640x360 preset=1 result=0x00000001
--test finished: 300/300
"""

EVAL_FAIL = """\
[host] NVSDK_NGX_D3D12_Init -> 0x00000001 (Success)
[pure] direct feature 18 ready: 640x360 preset=0 result=0x00000001
[host] evaluate failed 0xBAD00004 (?)
"""

CREATE_FAIL = """\
[host] NVSDK_NGX_D3D12_Init -> 0x00000001 (Success)
[pure] NS_NGX_VIA_CORE=1: feature 18 goes through NGX Core
[pure] direct feature 18 create failed 0xBAD0000B (UnableToInitializeFeature)
"""

BLOCKED = """\
 RESULT: BLOCKED - fix the prerequisites above first
missing: /repo/native/nvngx_dlssnr.dll
"""


def test_a_full_pass_is_pass():
    tool = load_tool()
    result = tool.parse(PASS)
    assert result["create"]["ok"] and result["create"]["preset"] == 1
    assert result["finished"] == {"good": 300, "total": 300}
    assert tool.verdict(result) == "PASS"


def test_evaluate_failure_names_evaluate():
    tool = load_tool()
    result = tool.parse(EVAL_FAIL)
    assert result["create"]["ok"]
    assert result["evaluate"]["code"] == "0xBAD00004"
    assert tool.verdict(result) == "evaluate 0xBAD00004"


def test_create_failure_names_create_and_the_core_path():
    tool = load_tool()
    result = tool.parse(CREATE_FAIL)
    assert result["create"]["ok"] is False
    assert result["create"]["code"] == "0xBAD0000B"
    assert result["via_core"] is True
    assert tool.verdict(result) == "create 0xBAD0000B"


def test_a_blocked_run_has_no_stage_to_name():
    tool = load_tool()
    result = tool.parse(BLOCKED)
    assert result["init"] is None and result["create"] is None
    assert tool.verdict(result) != "PASS"


def test_a_short_loop_is_not_a_pass():
    tool = load_tool()
    result = tool.parse(PASS.replace("300/300", "0/300"))
    assert tool.verdict(result).startswith("loop 0/300")