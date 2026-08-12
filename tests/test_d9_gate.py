"""D9 门禁测试（v0.2 spec T1 a-f + T2 解析错误）。

validate_d9 的职责边界：结构错误（fixture 非法 YAML / 缺字段）→ errors（阻断）；
门槛/命中/不可解析 → warnings（降级提示，不阻断）。
"""

from pathlib import Path
import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import validate_config as vc


def _scoring(dim_name="test_pass_rate", signal="my-check"):
    # 默认 signal 用非豁免命令（"pytest -q" 是 KNOWN_EXEMPT，会绕过 D9）
    return {
        "dimensions": [
            {"name": dim_name, "type": "hard", "weight": 1.0, "signal": signal}
        ],
        "aggregate": {
            "hard": "arithmetic_mean",
            "soft": "weighted_mean",
            "final": {"formula": "0.6*hard + 0.4*soft"},
        },
    }


def _write_fixture(root: Path, name: str, samples: list) -> Path:
    fixtures = root / "fixtures"
    fixtures.mkdir(exist_ok=True)
    path = fixtures / f"{name}.yaml"
    lines = [f"- input: {text}\n  expect: {expect}" for text, expect in samples]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _samples(n_pos=15, n_neg=15):
    return [("p", "pass") for _ in range(n_pos)] + [("n", "fail") for _ in range(n_neg)]


def _d9_command(positive_hit=15, negative_reject=15, total=30) -> str:
    """假 D9 模式命令：输出固定 JSON schema（A-min 约定）。"""
    body = (
        f"import json; print(json.dumps({{'total': {total}, "
        f"'positive_hit': {positive_hit}, 'negative_reject': {negative_reject}}}))"
    )
    return f'python -c "{body}"'


def test_missing_fixture_warns_downgrade(tmp_path):
    """(a) hard dimension 缺 fixture-set → warning（降级提示），非 error。"""
    errs, warns = vc.validate_d9(_scoring(), tmp_path)
    assert errs == []
    assert any("fixture" in w and "降级" in w for w in warns)


def test_fixture_too_few_samples_warns(tmp_path):
    """(b) fixture-set < 20 条 → warning（降级提示）。"""
    _write_fixture(tmp_path, "test_pass_rate", _samples(n_pos=5, n_neg=5))
    errs, warns = vc.validate_d9(_scoring(), tmp_path)
    assert errs == []
    assert any("20" in w and "降级" in w for w in warns)


def test_pass_when_fixture_and_hits_ok(tmp_path):
    """(c) fixture 数量 + 命中均达标 → 无 warning。"""
    _write_fixture(tmp_path, "test_pass_rate", _samples())
    errs, warns = vc.validate_d9(_scoring(signal=_d9_command()), tmp_path)
    assert errs == []
    assert warns == []


def test_low_hit_warns_downgrade(tmp_path):
    """(d) 数量达标但命中 <80% → warning（降级提示）。"""
    _write_fixture(tmp_path, "test_pass_rate", _samples())
    errs, warns = vc.validate_d9(
        _scoring(signal=_d9_command(positive_hit=5, negative_reject=5)), tmp_path
    )
    assert errs == []
    assert any("命中" in w and "降级" in w for w in warns)


def test_pass_again_when_hits_ok(tmp_path):
    """(e) 数量 + 命中均达标（不同样本数变体）→ 无 warning。"""
    _write_fixture(tmp_path, "test_pass_rate", _samples(n_pos=10, n_neg=10))
    errs, warns = vc.validate_d9(
        _scoring(signal=_d9_command(total=20, positive_hit=10, negative_reject=10)),
        tmp_path,
    )
    assert errs == []
    assert warns == []


def test_exempt_community_command_skips_d9(tmp_path):
    """(f) KNOWN_EXEMPT 社区共识工具名（pytest）→ 无 fixture 也跳过放行。"""
    errs, warns = vc.validate_d9(_scoring(signal="pytest -q"), tmp_path)
    assert errs == []
    assert warns == []


def test_exempt_pytest_variants(tmp_path):
    """(f 变体) pytest 工具名豁免覆盖常见变体（C-改1）：pytest / pytest -q -x / pytest -q --tb=short。"""
    for sig in ("pytest", "pytest -q -x", "pytest -q --tb=short"):
        errs, warns = vc.validate_d9(_scoring(signal=sig), tmp_path)
        assert errs == [] and warns == [], f"signal={sig!r} 应豁免"


def test_single_side_too_few_warns(tmp_path):
    """(D-改1) 总量 ≥20 但单侧 <10（15 pos + 4 neg）→ warning 降级。"""
    _write_fixture(tmp_path, "test_pass_rate", _samples(n_pos=15, n_neg=4))
    errs, warns = vc.validate_d9(_scoring(signal=_d9_command(total=19)), tmp_path)
    assert errs == []
    assert any("样本不足" in w and "降级" in w for w in warns)


def test_total_mismatch_warns(tmp_path):
    """(D-改2) D9 命令 total 与 fixture 样本数不一致 → warning 降级（命令未跑全）。"""
    _write_fixture(tmp_path, "test_pass_rate", _samples())
    errs, warns = vc.validate_d9(_scoring(signal=_d9_command(total=10)), tmp_path)
    assert errs == []
    assert any("不一致" in w and "降级" in w for w in warns)


def test_empty_fixture_is_error(tmp_path):
    """(B-改4) fixture 空文件（0 字节）→ error（必须是列表）。"""
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir(exist_ok=True)
    (fixtures / "test_pass_rate.yaml").write_text("", encoding="utf-8")
    errs, warns = vc.validate_d9(_scoring(), tmp_path)
    assert any("列表" in e for e in errs)
    assert warns == []


def test_soft_dimension_not_checked(tmp_path):
    """soft dimension 不触发 D9 检查。"""
    scoring = {
        "dimensions": [
            {"name": "clarity", "type": "soft", "weight": 1.0, "signal": "judge_prompt"}
        ],
        "aggregate": {
            "hard": "arithmetic_mean",
            "soft": "weighted_mean",
            "final": {"formula": "0.6*hard + 0.4*soft"},
        },
    }
    errs, warns = vc.validate_d9(scoring, tmp_path)
    assert errs == []
    assert warns == []


def test_malformed_fixture_is_error(tmp_path):
    """(T2) fixture 非法 YAML → error（配置坏了要修，不是降级）。"""
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir(exist_ok=True)
    (fixtures / "test_pass_rate.yaml").write_text(": : : bad", encoding="utf-8")
    errs, warns = vc.validate_d9(_scoring(), tmp_path)
    assert any("非法" in e for e in errs)
    assert warns == []


def test_missing_expect_field_is_error(tmp_path):
    """(T2) fixture 缺 expect 字段 → error。"""
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir(exist_ok=True)
    (fixtures / "test_pass_rate.yaml").write_text(
        "- input: only-input\n", encoding="utf-8"
    )
    errs, warns = vc.validate_d9(_scoring(), tmp_path)
    assert any("expect" in e for e in errs)
    assert warns == []


def test_unparsable_command_output_warns_downgrade(tmp_path):
    """命令未实现 D9 模式（输出不可解析）→ warning（降级提示），非 error。"""
    _write_fixture(tmp_path, "test_pass_rate", _samples())
    errs, warns = vc.validate_d9(_scoring(signal="echo not-json"), tmp_path)
    assert errs == []
    assert any("D9" in w or "解析" in w for w in warns)


def test_main_reads_target_path_from_config(tmp_path):
    """v0.2.1 commit 锁：main() 从 config.yaml.target_path 读 fixture 目录，
    不再 fallback 到 scoring.yaml 所在目录（spec D2/D9 + iter.sh:82 单路径对齐）。

    验证策略：把 scoring.yaml 与 target_path 隔离到 tmp_path 不同子目录，
    fixture 只放在 target_path/fixtures/ 下；若 main() 正确读 config.yaml → 无
    "缺 fixture-set" warning；若错读 scoring.yaml 所在目录 → 必报 warning。
    """
    import contextlib
    import io

    scoring_dir = tmp_path / "scoring_dir"
    target_dir = tmp_path / "target_dir"
    scoring_dir.mkdir()
    target_dir.mkdir()

    scoring = {
        "dimensions": [
            {
                "name": "test_pass_rate",
                "type": "hard",
                "weight": 1.0,
                "signal": 'python -c "import json; print(json.dumps({\'total\': 30, \'positive_hit\': 15, \'negative_reject\': 15}))"',
            }
        ],
        "aggregate": {
            "hard": "arithmetic_mean",
            "soft": "weighted_mean",
            "final": {"formula": "0.6*hard + 0.4*soft"},
        },
    }
    scoring_path = scoring_dir / "scoring.yaml"
    scoring_path.write_text(yaml.safe_dump(scoring, allow_unicode=True), encoding="utf-8")

    config = {
        "target_path": str(target_dir),
        "writer": "writer",
        "judge": "judge",
        "program": {"objective": "test", "constraints": ["c1"]},
        "automations": {"iter_timeout_minutes": 5},
    }
    config_path = scoring_dir / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")

    # fixture 仅放 target_dir/fixtures/（不在 scoring_dir 下）
    _write_fixture(target_dir, "test_pass_rate", _samples())

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = vc.main([str(scoring_path), str(config_path)])
    output = buf.getvalue()

    assert rc == 0
    assert "缺 fixture-set" not in output, (
        f"main() 应从 config.yaml.target_path 读 fixture 目录，但报缺 fixture:\n{output}"
    )

