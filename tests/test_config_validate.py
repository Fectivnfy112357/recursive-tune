"""T2 · 配置校验测试（spec T2 P1）。"""

import copy
import sys
from pathlib import Path

import yaml
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import validate_config as vc

VALID_SCORING = {
    "dimensions": [
        {"name": "test_pass_rate", "type": "hard", "weight": 1.0, "signal": "pytest -q"},
        {"name": "clarity", "type": "soft", "weight": 1.0, "signal": "judge_prompt"},
    ],
    "aggregate": {
        "hard": "arithmetic_mean",
        "soft": "weighted_mean",
        "final": {"formula": "0.6*hard + 0.4*soft", "default": True},
    },
}

VALID_CONFIG = {
    "target_path": "./demo-target",
    "writer": "writer",
    "judge": "judge",
    "program": {
        "objective": "让 demo-target 的 pytest 全绿",
        "constraints": ["只允许修改 demo-target/config.py", "禁止修改 test_config.py"],
    },
    "automations": {"iter_timeout_minutes": 5},
}


def write_yaml(tmp_path, name, data):
    p = tmp_path / name
    p.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return p


# --- scoring.yaml 校验 ---

def test_valid_scoring_passes():
    assert vc.validate_scoring(VALID_SCORING) == []


def test_scoring_missing_hard_dimension_fails():
    data = copy.deepcopy(VALID_SCORING)
    data["dimensions"] = [
        {"name": "clarity", "type": "soft", "weight": 1.0, "signal": "judge_prompt"}
    ]
    errors = vc.validate_scoring(data)
    assert any("hard" in e for e in errors)


def test_scoring_empty_dimensions_fails():
    data = copy.deepcopy(VALID_SCORING)
    data["dimensions"] = []
    assert vc.validate_scoring(data)


def test_scoring_invalid_type_fails():
    data = copy.deepcopy(VALID_SCORING)
    data["dimensions"][0]["type"] = "medium"
    assert any("hard|soft" in e for e in vc.validate_scoring(data))


def test_scoring_weight_out_of_range_fails():
    data = copy.deepcopy(VALID_SCORING)
    data["dimensions"][0]["weight"] = 1.5
    assert any("weight" in e for e in vc.validate_scoring(data))


def test_scoring_hard_dimension_with_judge_prompt_signal_fails():
    data = copy.deepcopy(VALID_SCORING)
    data["dimensions"][0]["signal"] = "judge_prompt"
    assert any("hard 维度的 signal" in e for e in vc.validate_scoring(data))


def test_scoring_missing_aggregate_fails():
    data = copy.deepcopy(VALID_SCORING)
    del data["aggregate"]
    assert any("aggregate" in e for e in vc.validate_scoring(data))


# --- config.yaml 校验 ---

def test_valid_config_passes():
    assert vc.validate_config(VALID_CONFIG) == []


def test_config_missing_required_keys_fails():
    data = copy.deepcopy(VALID_CONFIG)
    del data["judge"]
    errors = vc.validate_config(data)
    assert any("judge" in e for e in errors)


def test_config_bad_automations_timeout_fails():
    data = copy.deepcopy(VALID_CONFIG)
    data["automations"] = {"iter_timeout_minutes": 0}
    assert any("iter_timeout_minutes" in e for e in vc.validate_config(data))


def test_config_aggregate_override_is_optional():
    data = copy.deepcopy(VALID_CONFIG)
    data["aggregate"] = {"final": {"formula": "1.0*hard + 0.0*soft"}}
    assert vc.validate_config(data) == []


# --- aggregate 覆盖 ---

def test_effective_aggregate_defaults_to_scoring():
    assert vc.effective_aggregate(VALID_SCORING, VALID_CONFIG) == VALID_SCORING["aggregate"]


def test_effective_aggregate_config_overrides():
    config = copy.deepcopy(VALID_CONFIG)
    config["aggregate"] = {"final": {"formula": "1.0*hard + 0.0*soft"}}
    result = vc.effective_aggregate(VALID_SCORING, config)
    # config 只覆盖出现的字段；hard/soft 归约继承 scoring.yaml（deep-merge）
    assert result["final"]["formula"] == "1.0*hard + 0.0*soft"
    assert result["hard"] == "arithmetic_mean"
    assert result["soft"] == "weighted_mean"


def test_scoring_invalid_aggregate_enum_fails():
    data = copy.deepcopy(VALID_SCORING)
    data["aggregate"]["hard"] = "geometric_mean"
    assert any("aggregate.hard" in e for e in vc.validate_scoring(data))

    data = copy.deepcopy(VALID_SCORING)
    data["aggregate"]["soft"] = "geometric_mean"
    assert any("aggregate.soft" in e for e in vc.validate_scoring(data))


def test_scoring_soft_dimension_must_use_judge_prompt():
    data = copy.deepcopy(VALID_SCORING)
    data["dimensions"][1]["signal"] = "pytest -q"
    assert any("soft 维度的 signal" in e for e in vc.validate_scoring(data))


def test_config_required_values_must_be_nonempty_strings():
    for key in ("target_path", "writer", "judge"):
        data = copy.deepcopy(VALID_CONFIG)
        data[key] = ""
        assert any(key in e for e in vc.validate_config(data))

        data = copy.deepcopy(VALID_CONFIG)
        data[key] = 123
        assert any(key in e for e in vc.validate_config(data))


def test_config_aggregate_final_must_be_mapping_if_present():
    data = copy.deepcopy(VALID_CONFIG)
    data["aggregate"] = {"final": "0.6*hard"}
    assert any("aggregate.final" in e for e in vc.validate_config(data))


def test_config_missing_program_fails():
    data = copy.deepcopy(VALID_CONFIG)
    del data["program"]
    assert any("program" in e for e in vc.validate_config(data))


def test_config_program_bad_objective_fails():
    data = copy.deepcopy(VALID_CONFIG)
    data["program"]["objective"] = ""
    assert any("program.objective" in e for e in vc.validate_config(data))


def test_config_program_bad_constraints_fails():
    data = copy.deepcopy(VALID_CONFIG)
    data["program"]["constraints"] = []
    assert any("program.constraints" in e for e in vc.validate_config(data))

    data = copy.deepcopy(VALID_CONFIG)
    data["program"]["constraints"] = ["ok", ""]
    assert any("program.constraints[1]" in e for e in vc.validate_config(data))


# --- eval_formula（安全求值，ast 白名单） ---

def test_eval_formula_basic():
    assert vc.eval_formula("0.6*hard + 0.4*soft", 1.0, 0.5) == 0.6 * 1.0 + 0.4 * 0.5
    assert vc.eval_formula("1.0*hard + 0.0*soft", 1.0, 0.0) == 1.0
    assert vc.eval_formula("hard", 0.8, 0.2) == 0.8
    assert vc.eval_formula("(hard + soft)/2", 0.6, 0.4) == 0.5


def test_eval_formula_rejects_unsafe():
    # eval 沙箱经典逃逸链（纯属性访问，不需要 builtins）必须被 ast 白名单拒绝
    with pytest.raises(ValueError):
        vc.eval_formula("__import__('os').system('echo pwned')", 0.0, 0.0)
    with pytest.raises(ValueError):
        vc.eval_formula("hard.__class__.__mro__[1].__subclasses__()", 0.0, 0.0)
    with pytest.raises((ValueError, ZeroDivisionError)):
        vc.eval_formula("1/0", 0.0, 0.0)


def test_scoring_invalid_formula_fails():
    data = copy.deepcopy(VALID_SCORING)
    data["aggregate"]["final"]["formula"] = "__import__('os')"
    assert any("formula" in e for e in vc.validate_scoring(data))


# --- 端到端（文件读入） ---

def test_load_and_validate_ok(tmp_path):
    write_yaml(tmp_path, "scoring.yaml", VALID_SCORING)
    write_yaml(tmp_path, "config.yaml", VALID_CONFIG)
    assert vc.load_and_validate(tmp_path / "scoring.yaml", tmp_path / "config.yaml") == []


def test_load_and_validate_missing_file_fails(tmp_path):
    write_yaml(tmp_path, "scoring.yaml", VALID_SCORING)
    errors = vc.load_and_validate(tmp_path / "scoring.yaml", tmp_path / "nope.yaml")
    assert any("文件不存在" in e for e in errors)


def test_load_and_validate_bad_yaml_fails(tmp_path):
    (tmp_path / "scoring.yaml").write_text("dimensions: [unclosed", encoding="utf-8")
    write_yaml(tmp_path, "config.yaml", VALID_CONFIG)
    errors = vc.load_and_validate(tmp_path / "scoring.yaml", tmp_path / "config.yaml")
    assert any("非法 YAML" in e for e in errors)


def test_main_exit_codes(tmp_path):
    write_yaml(tmp_path, "scoring.yaml", VALID_SCORING)
    write_yaml(tmp_path, "config.yaml", VALID_CONFIG)
    assert vc.main([str(tmp_path / "scoring.yaml"), str(tmp_path / "config.yaml")]) == 0

    write_yaml(tmp_path, "scoring2.yaml", {
        "dimensions": [{"name": "only_soft", "type": "soft", "weight": 1.0, "signal": "judge_prompt"}],
        "aggregate": VALID_SCORING["aggregate"],
    })
    with pytest.raises(SystemExit) as exc:
        vc.main([str(tmp_path / "scoring2.yaml"), str(tmp_path / "config.yaml")])
    assert exc.value.code == 1
