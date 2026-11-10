# -*- coding: utf-8 -*-
"""稳定输出 JSON 和便于阅读的 Markdown 报告。"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import AnalysisResult
from .state_machines import CheckTaskMachine


def build_report(
    result: AnalysisResult,
    *,
    team_id: str,
    commit: str,
    checked_at: datetime,
    current_version: str,
    state_machine: CheckTaskMachine,
) -> dict[str, Any]:
    requirement_ids = {requirement.id for requirement in result.requirements}
    report = {
        "team_id": team_id,
        "project": "B",
        "commit": commit,
        "checked_at": checked_at.isoformat(),
        "read_only": True,
        "requirements": result.requirements_summary,
        "tests": result.tests_summary,
        "coverage": result.coverage,
        "regression": result.regression,
        "rtm": result.rtm_rows,
        "reverse_rtm": [
            {
                "test": test.id,
                "covers": list(test.covers),
                "kind": test.kind,
                "result": test.result,
                "status": (
                    "有效引用"
                    if test.covers and all(
                        ref in requirement_ids for ref in test.covers
                    )
                    else "孤儿或非法引用"
                ),
                "location": f"{test.file}:{test.line}",
            }
            for test in result.tests
        ],
        "entry_states": dict(sorted(result.entry_states.items())),
        "state_machines": {
            "check_task": {
                "state": state_machine.state,
                "history": state_machine.history,
            },
            "change_regression": {
                "state": result.regression.get("state"),
                "history": result.regression.get("history", []),
            },
        },
        "srs_version": current_version,
        "issues": [issue.to_dict() for issue in result.issues],
    }
    stable_payload = {
        key: value for key, value in report.items() if key != "checked_at"
    }
    report["result_digest"] = hashlib.sha256(
        json.dumps(
            stable_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return report


def write_json(report: dict[str, Any], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target


def _cell(value: object) -> str:
    text = str(value).replace("|", "\\|").replace("\n", " ")
    return text or "-"


def write_markdown(report: dict[str, Any], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    requirements = report["requirements"]
    tests = report["tests"]
    regression = report["regression"]
    lines = [
        "# 需求—测试追溯检查报告",
        "",
        f"- 组号：{report['team_id']}",
        f"- 被检查 commit：`{report['commit']}`",
        f"- SRS 版本：`{report['srs_version']}`",
        f"- 检查时间：{report['checked_at']}",
        "- 只读：是",
        f"- 任务状态：{report['state_machines']['check_task']['state']}",
        "",
        "## 汇总",
        "",
        "| 指标 | 数值 |",
        "| --- | --- |",
        f"| FR 总数 / 已覆盖 | {requirements['total']} / {requirements['covered']} |",
        f"| FR 覆盖率 | {report['coverage']['fr']:.2%} |",
        f"| 关键 FR 边界覆盖率 | {report['coverage']['critical_boundary']:.2%} |",
        f"| 关键 FR 正常覆盖率 | {report['coverage']['critical_happy']:.2%} |",
        f"| TC 总数 / 孤儿 | {tests['total']} / {len(tests['orphan'])} |",
        f"| 变更回归状态 | {regression['status']} |",
        "",
        "## 双向追溯矩阵",
        "",
        "| 需求 | 关键 | 全部用例 | PASS 用例 | 正常 | 边界 | 无效 | 状态 | 需求位置 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["rtm"]:
        kinds = row["kinds"]
        lines.append(
            "| {requirement} | {critical} | {tests} | {passing} | {happy} | "
            "{boundary} | {invalid} | {status} | {location} |".format(
                requirement=_cell(row["requirement"]),
                critical="是" if row["critical"] else "否",
                tests=_cell("、".join(row["tests"])),
                passing=_cell("、".join(row["passing"])),
                happy="是" if kinds["happy"] else "否",
                boundary="是" if kinds["boundary"] else "否",
                invalid="是" if kinds["invalid"] else "否",
                status=_cell(row["status"]),
                location=_cell(row["requirement_location"]),
            )
        )
    lines += [
        "",
        "## 用例到需求的反向表",
        "",
        "| 用例 | 引用需求 | 类型 | 实际结果 | 状态 | 用例位置 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["reverse_rtm"]:
        lines.append(
            f"| {_cell(row['test'])} | {_cell('、'.join(row['covers']))} | "
            f"{_cell(row['kind'])} | {_cell(row['result'])} | "
            f"{_cell(row['status'])} | {_cell(row['location'])} |"
        )
    lines += ["", "## 差异清单", ""]
    issues = report["issues"]
    if not issues:
        lines.append("未发现问题。")
    else:
        lines += [
            "| 严重度 | 问题码 | 编号 | 证据位置 | 说明 |",
            "| --- | --- | --- | --- | --- |",
        ]
        for issue in issues:
            location = "-"
            if issue.get("file"):
                location = issue["file"]
                if issue.get("line"):
                    location += f":{issue['line']}"
            lines.append(
                f"| {_cell(issue['severity'])} | {_cell(issue['code'])} | "
                f"{_cell(issue.get('ref'))} | {_cell(location)} | "
                f"{_cell(issue['evidence'])} |"
            )
    lines += [
        "",
        "## 变更影响",
        "",
        f"- 修改或删除的 FR：{'、'.join(regression['changed_fr']) or '无'}",
        f"- 受影响 TC：{'、'.join(regression['affected_tests']) or '无'}",
        f"- 待回归 TC：{'、'.join(regression['pending']) or '无'}",
        "",
        "> 本报告只检查结构化输入中的映射与一致性。未结构化文本必须人工确认，系统不会自动定稿。",
        "",
    ]
    target.write_text("\n".join(lines), encoding="utf-8")
    return target
