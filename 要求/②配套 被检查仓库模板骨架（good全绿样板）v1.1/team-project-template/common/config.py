# -*- coding: utf-8 -*-
"""读取评阅配置与花名册。仅依赖 PyYAML。

阈值以 assessment.yml 为准，本文件不内置任何具体数值。
"""
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("缺少依赖，请先执行：pip install -r requirements.txt") from exc


def load_yaml(path):
    """读取任意 YAML 文件并返回字典。"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_assessment(path="assessment.yml"):
    """返回评阅配置；校验里程碑与权重两段必须存在。"""
    data = load_yaml(path) or {}
    for key in ("milestones", "weights"):
        if key not in data:
            raise ValueError(f"assessment.yml 缺少必填段：{key}")
    return data


def load_roster(path="team-roster.yml"):
    """返回 (team_id, project, roster_dict)。"""
    data = load_yaml(path) or {}
    team = data.get("team", {})
    if not team.get("members"):
        raise ValueError("花名册 team.members 为空或不存在")
    return team.get("id"), team.get("project"), data


def threshold_for_project(assessment, project):
    """按选题返回对应阈值段：A->process，B->traceability，C->ai。"""
    mapping = {
        "A": "process_thresholds",
        "B": "traceability_thresholds",
        "C": "ai_thresholds",
    }
    return assessment.get(mapping.get(project, ""), {}) or {}
