# -*- coding: utf-8 -*-
"""统一报告 JSON 基类。

核心问题判定（问题码、阈值、状态机）由各组完成；本文件只保证公共字段齐全、
JSON 可序列化、UTF-8 落盘，并固定 read_only=True。
"""
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

_CN_TZ = timezone(timedelta(hours=8))


class Severity:
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class Issue:
    code: str
    severity: str = Severity.MEDIUM
    evidence: str = ""
    loc: dict = field(default_factory=dict)  # 如 line/ref/commit/entry/milestone

    def to_dict(self):
        d = {"code": self.code, "severity": self.severity, "evidence": self.evidence}
        d.update(self.loc)
        return d


class ReportBuilder:
    def __init__(self, team_id, project, commit, read_only=True):
        self.data = {
            "team_id": team_id,
            "project": project,
            "commit": commit,
            "checked_at": datetime.now(_CN_TZ).isoformat(),
            "read_only": read_only,
            "issues": [],
        }

    def set(self, key, value):
        """设置子项目自定义字段，如 milestones/members/requirements/ai_log。"""
        self.data[key] = value
        return self

    def add_issue(self, issue):
        self.data["issues"].append(issue.to_dict() if isinstance(issue, Issue) else issue)
        return self

    def to_dict(self):
        return self.data

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        return path
