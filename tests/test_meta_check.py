"""T2 · meta_check.sh 测试固化（v0.2 spec T3 a-g）。

meta_check.sh 是 v0.2 新件（无 v0.1 prior art），本测试把验证步骤固化为可重复 pytest。
副作用防护：修改 docs/adr / state / scripts 的场景都用 fixture 备份并在结束时恢复。
"""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "meta_check.sh"
ADR_004 = ROOT / "docs" / "adr" / "ADR-004-meta-layer-target.md"
STATE_PROGRAM = ROOT / "state" / "program.md"
STATE_JUDGE = ROOT / "state" / "judge-prompt.md"


def run_meta(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args], capture_output=True, text=True, cwd=ROOT
    )


class _Backup:
    """备份一组文件，退出时恢复原内容。"""

    def __init__(self, *paths: Path):
        self._saved = [(p, p.read_bytes() if p.exists() else None) for p in paths]

    def restore(self) -> None:
        for p, data in self._saved:
            if data is None:
                p.unlink(missing_ok=True)
            else:
                p.write_bytes(data)


def test_normal_pass():
    """(a) 正常态：当前 5 份 ADR + 模板 + state 全过，exit 0。"""
    r = run_meta()
    assert r.returncode == 0, r.stdout + r.stderr
    assert "总评: PASS" in r.stdout


def test_json_output_structure():
    """(d) --json：overall 字段存在且为 PASS。"""
    r = run_meta("--json")
    assert r.returncode == 0, r.stdout + r.stderr
    assert '"overall": "PASS"' in r.stdout
    assert '"dimension_1_adr"' in r.stdout
    assert '"dimension_2_templates"' in r.stdout


def test_missing_adr_section_fails_dim1():
    """(b) 删 ADR-004 ## 后果 段 → 维度 1 FAIL，exit 1。"""
    bk = _Backup(ADR_004)
    try:
        content = ADR_004.read_text(encoding="utf-8")
        ADR_004.write_text(
            "\n".join(
                line for line in content.splitlines() if line != "## 后果"
            ),
            encoding="utf-8",
        )
        r = run_meta()
        assert r.returncode == 1, r.stdout + r.stderr
        assert "维度 1 总评: FAIL" in r.stdout
    finally:
        bk.restore()


def test_state_residual_fails_dim2():
    """(c) state/program.md 残留 {{...}} → 维度 2 FAIL，exit 1。"""
    bk = _Backup(STATE_PROGRAM)
    try:
        with STATE_PROGRAM.open("a", encoding="utf-8") as f:
            f.write("\n{{target_path}}\n")
        r = run_meta()
        assert r.returncode == 1, r.stdout + r.stderr
        assert "维度 2 总评: FAIL" in r.stdout
        assert "运行时残留" in r.stdout
    finally:
        bk.restore()


def test_missing_state_warns_not_blocks():
    """(f) state 缺失 → warning，默认不阻断（exit 0）。"""
    bk = _Backup(STATE_PROGRAM, STATE_JUDGE)
    try:
        STATE_PROGRAM.unlink(missing_ok=True)
        STATE_JUDGE.unlink(missing_ok=True)
        r = run_meta()
        assert r.returncode == 0, r.stdout + r.stderr
        assert "SKIP" in r.stdout
    finally:
        bk.restore()


def test_strict_upgrades_warning_to_error():
    """(e) --strict：state 缺失的 warning 升级为 error（exit 1）。"""
    bk = _Backup(STATE_PROGRAM, STATE_JUDGE)
    try:
        STATE_PROGRAM.unlink(missing_ok=True)
        STATE_JUDGE.unlink(missing_ok=True)
        r = run_meta("--strict")
        assert r.returncode == 1, r.stdout + r.stderr
        assert "总评: FAIL" in r.stdout
    finally:
        bk.restore()


def test_unknown_arg_usage_error():
    """退出码 2 = usage error（参数错）。"""
    r = run_meta("--bogus")
    assert r.returncode == 2, r.stdout + r.stderr


def test_exempt_mechanism_removal_fails():
    """(g) KNOWN_ADR_EXEMPT：把 ADR-003.5 移出豁免表 → 维度 1 FAIL。

    ADR-003.5 缺"备选方案（被否决）"段，豁免表是它 PASS 的唯一原因；
    移出豁免后必须 FAIL——证明豁免机制真实生效。
    """
    bk = _Backup(SCRIPT)
    try:
        script = SCRIPT.read_text(encoding="utf-8")
        assert '["ADR-003.5-A-class-target-domain.md"]' in script
        # 移出豁免：删掉该行
        patched = "\n".join(
            line
            for line in script.splitlines()
            if "ADR-003.5-A-class-target-domain.md" not in line
        )
        SCRIPT.write_text(patched, encoding="utf-8")
        r = run_meta()
        assert r.returncode == 1, r.stdout + r.stderr
        assert "维度 1 总评: FAIL" in r.stdout
        assert "ADR-003.5" in r.stdout
    finally:
        bk.restore()


def test_exempt_mechanism_addition_keeps_pass():
    """(g) KNOWN_ADR_EXEMPT：把标准 ADR-005 加入豁免表 → 仍 PASS（豁免不误伤标准 ADR）。"""
    bk = _Backup(SCRIPT)
    try:
        script = SCRIPT.read_text(encoding="utf-8")
        anchor = '  ["ADR-003.5-A-class-target-domain.md"]="备选方案（被否决）"\n'
        assert anchor in script
        added = anchor + '  ["ADR-005-v0.2-scope.md"]="备选方案（被否决）"  # test-only exemption\n'
        SCRIPT.write_text(script.replace(anchor, added), encoding="utf-8")
        r = run_meta()
        assert r.returncode == 0, r.stdout + r.stderr
        assert "总评: PASS" in r.stdout
    finally:
        bk.restore()
