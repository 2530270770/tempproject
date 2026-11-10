# -*- coding: utf-8 -*-
"""B 题需求—测试追溯检查器的命令行入口。"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from common.config import load_assessment, load_roster, threshold_for_project
from common.repo import readonly_clone

from .engine import TraceabilityEngine
from .parser import (
    parse_srs_file,
    parse_srs_text,
    parse_tests_file,
    srs_version_from_text,
)
from .permissions import authorize
from .reporting import build_report, write_json, write_markdown
from .state_machines import CheckTaskMachine, InvalidTransition

CN_TZ = timezone(timedelta(hours=8))


def _git_output(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(cwd), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git 命令执行失败")
    return proc.stdout.strip()


def _resolve_commit(target: Path, requested: str | None) -> str:
    if requested:
        return requested
    try:
        return _git_output(target, "rev-parse", "--short", "HEAD")
    except Exception:
        return "WORKTREE"


def _read_srs_at_ref(target: Path, ref: str, relative_srs: Path) -> list:
    text = _git_output(target, "show", f"{ref}:{relative_srs.as_posix()}")
    return parse_srs_text(text, f"<git:{ref}:{relative_srs.as_posix()}>")


def _test_files(tests_dir: Path) -> list[Path]:
    if not tests_dir.exists():
        raise FileNotFoundError(f"测试目录不存在：{tests_dir}")
    files: list[Path] = []
    for path in sorted(tests_dir.rglob("*.md")):
        relative_parts = set(path.relative_to(tests_dir).parts)
        if "fixtures" in relative_parts or "examples" in relative_parts:
            continue
        files.append(path)
    return files


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trace-check",
        description="B 项目：需求—测试追溯一致性检查器",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="检查一个符合统一约定的仓库")
    check.add_argument("target", nargs="?", default=".", help="被检查仓库根目录")
    check.add_argument("--srs", help="覆盖默认 SRS 路径")
    check.add_argument("--tests", help="覆盖默认 tests 路径")
    check.add_argument("--baseline", help="基线 SRS Markdown 文件")
    check.add_argument("--baseline-ref", help="从目标仓库 Git 历史读取基线 SRS")
    check.add_argument("--commit", help="报告中记录的提交；默认读取 HEAD")
    check.add_argument("--team-id", help="覆盖花名册中的组号")
    check.add_argument("--role", default="teacher", choices=("teacher", "ta", "student"))
    check.add_argument("--caller-team", help="已认证调用者组号，学生权限校验用")
    check.add_argument(
        "--output-dir",
        help="报告输出目录；默认写入系统临时目录",
    )
    check.add_argument("--confirm", action="store_true", help="记录人工确认并归档")
    check.add_argument(
        "--fail-on",
        choices=("none", "high", "any"),
        default="none",
        help="达到指定问题级别时返回非零退出码",
    )
    check.add_argument(
        "--repo-url",
        help="可选：只读克隆 GitLab 仓库；令牌只从 GITLAB_READ_TOKEN 读取",
    )
    check.add_argument("--ref", help="克隆仓库后检出的分支或提交")
    return parser


def _load_inputs(
    target: Path,
    *,
    srs_path: Path,
    tests_path: Path,
    baseline_path: Path | None,
    baseline_ref: str | None,
) -> tuple[list, list, list | None, str]:
    def stable_source(value: str) -> str:
        path = Path(value)
        if not path.is_absolute():
            return path.as_posix()
        try:
            return path.resolve().relative_to(target.resolve()).as_posix()
        except ValueError:
            return path.as_posix()

    requirements = [
        replace(requirement, file=stable_source(requirement.file))
        for requirement in parse_srs_file(srs_path)
    ]
    test_files = _test_files(tests_path)
    cases = [
        replace(case, file=stable_source(case.file))
        for test_file in test_files
        for case in parse_tests_file(test_file)
    ]
    if not requirements:
        raise ValueError(
            f"没有从 {srs_path} 解析到结构化 FR-xx；"
            "非结构化输入不得自动定稿，请人工整理后再检查"
        )
    if not cases:
        raise ValueError(f"没有从 {tests_path} 解析到 TC-xx；covers 字段必须使用冒号")
    baseline = None
    if baseline_path:
        baseline = [
            replace(requirement, file=stable_source(requirement.file))
            for requirement in parse_srs_file(baseline_path)
        ]
    elif baseline_ref:
        relative = srs_path.resolve().relative_to(target.resolve())
        baseline = _read_srs_at_ref(target, baseline_ref, relative)
    version = srs_version_from_text(srs_path.read_text(encoding="utf-8-sig"))
    return requirements, cases, baseline, version


def run_check(args: argparse.Namespace) -> int:
    original_target = Path(args.target).resolve()
    temp_context = None
    if args.repo_url:
        temp_context = tempfile.TemporaryDirectory(prefix="trace-check-")
        token = os.environ.get("GITLAB_READ_TOKEN")
        target = Path(readonly_clone(
            args.repo_url,
            Path(temp_context.name) / "repo",
            token=token,
            ref=args.ref,
            timeout=120,
        )).resolve()
    else:
        target = original_target
        if not target.exists():
            raise FileNotFoundError(f"目标仓库不存在：{target}")

    srs_path = Path(args.srs).resolve() if args.srs else (
        target / "docs" / "m1-立项与需求" / "SRS.md"
    )
    tests_path = Path(args.tests).resolve() if args.tests else target / "tests"
    baseline_path = Path(args.baseline).resolve() if args.baseline else None

    roster_team = "UNKNOWN"
    roster_path = target / "team-roster.yml"
    if roster_path.exists():
        team_id, _, _ = load_roster(roster_path)
        roster_team = team_id or "UNKNOWN"
    team_id = args.team_id or roster_team
    authorize(
        args.role,
        "run_check",
        caller_team=args.caller_team,
        target_team=team_id,
    )
    if args.confirm:
        authorize(args.role, "confirm")

    assessment_path = target / "assessment.yml"
    thresholds = {}
    if assessment_path.exists():
        thresholds = threshold_for_project(load_assessment(assessment_path), "B")

    machine = CheckTaskMachine()
    machine.trigger("PARSE")
    try:
        requirements, cases, baseline, version = _load_inputs(
            target,
            srs_path=srs_path,
            tests_path=tests_path,
            baseline_path=baseline_path,
            baseline_ref=args.baseline_ref,
        )
    except Exception:
        machine.trigger("FAIL")
        raise

    machine.trigger("CHECK")
    try:
        engine = TraceabilityEngine(
            min_cases_per_fr=thresholds.get("min_cases_per_fr", 1),
            critical_requires_boundary=thresholds.get(
                "critical_requires_boundary", True
            ),
            critical_requires_happy=thresholds.get(
                "critical_requires_happy", True
            ),
        )
        result = engine.analyze(
            requirements,
            cases,
            baseline=baseline,
            current_version=version,
        )
    except Exception:
        machine.trigger("FAIL")
        raise
    machine.trigger("REPORT")
    if args.confirm:
        machine.trigger("CONFIRM")
        machine.trigger("ARCHIVE")

    commit = _resolve_commit(target, args.commit)
    report = build_report(
        result,
        team_id=team_id,
        commit=commit,
        checked_at=datetime.now(CN_TZ),
        current_version=version,
        state_machine=machine,
    )
    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else Path(tempfile.gettempdir()).resolve() / "trace-check-reports"
    )
    try:
        output_dir.relative_to(target)
    except ValueError:
        pass
    else:
        raise ValueError("报告输出目录不得位于被检查仓库内部")
    slug = target.name or "repository"
    json_path = output_dir / f"{slug}-{commit}.json"
    md_path = output_dir / f"{slug}-{commit}-RTM.md"
    write_json(report, json_path)
    write_markdown(report, md_path)

    high_count = sum(1 for issue in result.issues if issue.severity == "HIGH")
    print(json.dumps({
        "state": machine.state,
        "requirements": result.requirements_summary,
        "tests": result.tests_summary,
        "coverage": result.coverage,
        "issues": len(result.issues),
        "high": high_count,
        "json": str(json_path),
        "rtm": str(md_path),
    }, ensure_ascii=False))
    if temp_context:
        temp_context.cleanup()
    if args.fail_on == "any" and result.issues:
        return 2
    if args.fail_on == "high" and high_count:
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = _parser().parse_args(argv)
    try:
        if args.command == "check":
            return run_check(args)
        raise InvalidTransition(f"未知命令：{args.command}")
    except (ValueError, OSError, RuntimeError, PermissionError, InvalidTransition) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
