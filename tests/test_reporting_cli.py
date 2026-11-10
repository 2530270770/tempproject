# -*- coding: utf-8 -*-
import contextlib
import io
import json
import shutil
import subprocess
import tempfile
import time
import unittest
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

from src.traceability.cli import _parser, main, run_check
from src.traceability.engine import TraceabilityEngine
from src.traceability.parser import parse_srs_text, parse_tests_text
from src.traceability.reporting import build_report
from src.traceability.state_machines import CheckTaskMachine

from tests import (
    BAD_SRS,
    BAD_TESTS,
    GOOD_SRS,
    GOOD_TESTS,
    REGRESSION_BASELINE_SRS,
    REGRESSION_CURRENT_SRS,
    REGRESSION_TESTS,
    write_repository,
)

ROOT = Path(__file__).resolve().parents[1]


class ReportingAndCliTests(unittest.TestCase):
    def _args(self, target, output_dir, *extra, confirm=False, fail_on="none"):
        argv = [
            "check", str(target),
            "--output-dir", str(output_dir),
            "--role", "teacher",
            *extra,
        ]
        if confirm:
            argv.append("--confirm")
        argv += ["--fail-on", fail_on]
        args = _parser().parse_args(argv)
        return args

    def test_cli_writes_json_and_markdown_with_line_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = write_repository(
                Path(temp) / "bad-repo",
                srs=BAD_SRS,
                tests=BAD_TESTS,
            )
            output = Path(temp)
            args = self._args(repo, output)
            with contextlib.redirect_stdout(io.StringIO()):
                code = run_check(args)
            self.assertEqual(0, code)
            json_files = list(output.glob("*.json"))
            md_files = list(output.glob("*.md"))
            self.assertEqual(1, len(json_files))
            self.assertEqual(1, len(md_files))
            report = json.loads(json_files[0].read_text(encoding="utf-8"))
            self.assertEqual("差异报告", report["state_machines"]["check_task"]["state"])
            self.assertEqual(5, len(report["reverse_rtm"]))
            self.assertIn("MISSING_TEST", {item["code"] for item in report["issues"]})
            required = {"code", "severity", "evidence", "ref", "file", "line"}
            for issue in report["issues"]:
                self.assertTrue(required <= set(issue))
                self.assertFalse(Path(issue["file"]).is_absolute())
            self.assertIn("需求—测试追溯检查报告", md_files[0].read_text(encoding="utf-8"))

    def test_cli_confirm_archives(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = write_repository(
                Path(temp) / "good-repo",
                srs=GOOD_SRS,
                tests=GOOD_TESTS,
            )
            output = Path(temp) / "reports"
            args = self._args(repo, output, confirm=True)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, run_check(args))
            report = json.loads(
                next(output.glob("*.json")).read_text(encoding="utf-8")
            )
            self.assertEqual("已归档", report["state_machines"]["check_task"]["state"])
            self.assertEqual([], report["issues"])

    def test_engine_is_deterministic_except_checked_time(self):
        requirements = parse_srs_text(BAD_SRS)
        cases = parse_tests_text(BAD_TESTS)
        first = TraceabilityEngine().analyze(requirements, cases, current_version="v1")
        second = TraceabilityEngine().analyze(requirements, cases, current_version="v1")
        self.assertEqual(first.requirements_summary, second.requirements_summary)
        self.assertEqual(first.tests_summary, second.tests_summary)
        self.assertEqual(
            [issue.to_dict() for issue in first.issues],
            [issue.to_dict() for issue in second.issues],
        )
        machine_one = CheckTaskMachine()
        machine_one.trigger("PARSE")
        machine_one.trigger("CHECK")
        machine_one.trigger("REPORT")
        machine_two = CheckTaskMachine()
        machine_two.trigger("PARSE")
        machine_two.trigger("CHECK")
        machine_two.trigger("REPORT")
        first_report = build_report(
            first, team_id="T01", commit="abc123",
            checked_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            current_version="v1", state_machine=machine_one,
        )
        second_report = build_report(
            second, team_id="T01", commit="abc123",
            checked_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            current_version="v1", state_machine=machine_two,
        )
        self.assertNotEqual(first_report["checked_at"], second_report["checked_at"])
        self.assertEqual(first_report["result_digest"], second_report["result_digest"])

    def test_fail_on_high_returns_quality_gate_code(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = write_repository(
                Path(temp) / "bad-repo",
                srs=BAD_SRS,
                tests=BAD_TESTS,
            )
            args = self._args(
                repo,
                Path(temp),
                fail_on="high",
            )
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(2, run_check(args))

    def test_student_cannot_check_own_team_via_cli(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = write_repository(
                Path(temp) / "good-repo",
                srs=GOOD_SRS,
                tests=GOOD_TESTS,
                team_id="T01",
            )
            argv = [
                "check", str(repo),
                "--team-id", "T01",
                "--role", "student",
                "--caller-team", "T01",
                "--output-dir", str(temp),
            ]
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(1, main(argv))
            self.assertIn("无权执行 run_check", stderr.getvalue())

    def test_output_directory_inside_target_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = write_repository(
                Path(temp) / "good-repo",
                srs=GOOD_SRS,
                tests=GOOD_TESTS,
            )
            output = repo / "reports"
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = main([
                    "check", str(repo),
                    "--output-dir", str(output),
                    "--role", "teacher",
                ])
            self.assertEqual(1, code)
            self.assertIn("不得位于被检查仓库内部", stderr.getvalue())
            self.assertFalse(output.exists())

    def test_missing_target_returns_error_code(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["check", str(ROOT / "__missing_target__")])
        self.assertEqual(1, code)
        self.assertIn("目标仓库不存在", stderr.getvalue())

    @unittest.skipUnless(shutil.which("git"), "git is not installed")
    def test_git_history_baseline(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "repo"
            docs = repo / "docs" / "m1-立项与需求"
            tests = repo / "tests"
            write_repository(
                repo,
                srs=REGRESSION_BASELINE_SRS,
                tests=REGRESSION_TESTS,
                team_id="T01",
            )

            def git(*args):
                subprocess.run(
                    ["git", "-C", str(repo), *args],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

            git("init", "--quiet")
            git("config", "user.email", "test@example.com")
            git("config", "user.name", "Test")
            git("add", ".")
            git("commit", "--quiet", "-m", "baseline")
            (docs / "SRS.md").write_text(REGRESSION_CURRENT_SRS, encoding="utf-8")
            git("add", ".")
            git("commit", "--quiet", "-m", "change")

            output = Path(temp) / "reports"
            argv = [
                "check", str(repo),
                "--baseline-ref", "HEAD~1",
                "--team-id", "T01",
                "--role", "teacher",
                "--output-dir", str(output),
            ]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, main(argv))
            report = json.loads(next(output.glob("*.json")).read_text(encoding="utf-8"))
            self.assertEqual(["FR-01", "FR-02"], report["regression"]["changed_fr"])
            self.assertEqual(["TC-01", "TC-02"], report["regression"]["pending"])

    def test_100_fr_300_tc_performance_budget(self):
        req_lines = [
            "| 编号 | 需求描述 | 优先级 | 验收标准 |",
            "| --- | --- | --- | --- |",
        ]
        for index in range(1, 101):
            req_lines.append(
                f"| FR-{index:02d} | 需求{index} | 必做 | 成功 |"
            )
        test_blocks = []
        case_no = 1
        for req_no in range(1, 101):
            for suffix in ("正常", "边界", "异常"):
                test_blocks.append(
                    f"用例编号: TC-{case_no:02d}\n"
                    f"covers: FR-{req_no:02d}\n"
                    f"类型: {suffix}\n"
                    "实际结果: PASS\n"
                )
                case_no += 1
        requirements = parse_srs_text("\n".join(req_lines))
        cases = parse_tests_text("\n\n".join(test_blocks))
        durations = []
        for _ in range(5):
            started = time.perf_counter()
            result = TraceabilityEngine().analyze(
                requirements,
                cases,
                current_version="v1",
            )
            durations.append(time.perf_counter() - started)
            self.assertEqual(1.0, result.coverage["fr"])
        median = sorted(durations)[len(durations) // 2]
        print(f"\nbenchmark_median_seconds={median:.6f}")
        self.assertLess(median, 10.0)


if __name__ == "__main__":
    unittest.main()
