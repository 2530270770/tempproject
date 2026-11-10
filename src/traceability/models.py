# -*- coding: utf-8 -*-
"""供解析器、规则引擎和报告模块使用的领域模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Requirement:
    id: str
    title: str
    description: str
    acceptance: str
    priority: str
    version: str
    critical: bool
    file: str
    line: int
    fingerprint: str


@dataclass(frozen=True)
class TestCase:
    id: str
    covers: tuple[str, ...]
    cover_raw: str
    kind: str
    result: str
    verified_version: str
    body: str
    file: str
    line: int
    fingerprint: str


@dataclass(frozen=True)
class Issue:
    code: str
    severity: str
    evidence: str
    ref: str | None = None
    file: str | None = None
    line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "code": self.code,
            "severity": self.severity,
            "evidence": self.evidence,
        }
        if self.ref:
            data["ref"] = self.ref
        if self.file:
            data["file"] = self.file
        if self.line is not None:
            data["line"] = self.line
        return data


@dataclass
class AnalysisResult:
    requirements: list[Requirement]
    tests: list[TestCase]
    issues: list[Issue] = field(default_factory=list)
    rtm_rows: list[dict[str, Any]] = field(default_factory=list)
    requirements_summary: dict[str, Any] = field(default_factory=dict)
    tests_summary: dict[str, Any] = field(default_factory=dict)
    coverage: dict[str, Any] = field(default_factory=dict)
    regression: dict[str, Any] = field(default_factory=dict)
    entry_states: dict[str, str] = field(default_factory=dict)

    def has_code(self, code: str) -> bool:
        return any(issue.code == code for issue in self.issues)

    def refs_for(self, code: str) -> list[str]:
        return sorted(
            issue.ref for issue in self.issues
            if issue.code == code and issue.ref is not None
        )
