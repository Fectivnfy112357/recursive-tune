"""T1 · templates 占位符与结构测试（spec T2 P2）。"""

from pathlib import Path
import re

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"

PROGRAM_PLACEHOLDERS = {"{{target_path}}", "{{objective}}", "{{constraints}}"}
JUDGE_PLACEHOLDERS = {"{{target_path}}", "{{dimensions}}", "{{diff}}"}
# 具体 Target 类型词：A 类无感知（spec D2）要求模板不点名任何具体目标内容
CONCRETE_TARGET_WORDS = ("SKILL.md", "config.yaml", "train.py")


def _placeholders(content: str) -> set[str]:
    # 占位符形如 {{小写字母/下划线}}；模板正文中只有待替换字段使用此形态
    return set(re.findall(r"\{\{[a-z_]+\}\}", content))


def test_program_template_has_exactly_three_placeholders():
    content = (TEMPLATES / "program.md.template").read_text(encoding="utf-8")
    assert _placeholders(content) == PROGRAM_PLACEHOLDERS


def test_program_template_fills_without_leftovers():
    content = (TEMPLATES / "program.md.template").read_text(encoding="utf-8")
    filled = content
    for ph in PROGRAM_PLACEHOLDERS:
        filled = filled.replace(ph, "filled")
    assert "{{" not in filled, "替换后不应残留任何占位符"


def test_program_template_has_d2_sections():
    """D2：头部任务陈述 → 中段约束清单 → 尾部验证说明（顺序）。"""
    content = (TEMPLATES / "program.md.template").read_text(encoding="utf-8")
    idx_task = content.index("任务陈述")
    idx_constraints = content.index("约束")
    idx_verify = content.index("验证")
    assert idx_task < idx_constraints < idx_verify


def test_judge_template_has_signal_guidance_and_schema():
    content = (TEMPLATES / "judge-prompt.md.template").read_text(encoding="utf-8")
    assert "Hard Signal 引导" in content
    assert "Soft Signal 引导" in content
    assert "scores:" in content
    assert "type: soft" in content


def test_judge_template_has_placeholders():
    content = (TEMPLATES / "judge-prompt.md.template").read_text(encoding="utf-8")
    assert _placeholders(content) == JUDGE_PLACEHOLDERS


def test_templates_are_target_agnostic():
    """A 类无感知：模板不得点名具体 Target 内容（spec D2 核心要求）。"""
    for name in ("program.md.template", "judge-prompt.md.template"):
        content = (TEMPLATES / name).read_text(encoding="utf-8")
        for word in CONCRETE_TARGET_WORDS:
            assert word not in content, f"{name} 不应包含具体 Target 词: {word}"
