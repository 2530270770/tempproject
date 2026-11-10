# -*- coding: utf-8 -*-
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from src.traceability.cli import main
from src.traceability.engine import TraceabilityEngine
from src.traceability.parser import (
    parse_srs_file,
    parse_srs_text,
    parse_tests_file,
)

from tests import (
    TEACHER_STANDARD_SRS,
    TEACHER_STANDARD_TEST_FILES,
    write_repository,
)


class TeacherReleaseSampleTests(unittest.TestCase):
    def _analyze(self, base: Path):
        requirements = parse_srs_file(
            base / "docs" / "m1-立项与需求" / "SRS.md"
        )
        cases = [
            case
            for path in sorted((base / "tests").glob("*.md"))
            for case in parse_tests_file(path)
        ]
        return TraceabilityEngine().analyze(
            requirements,
            cases,
            current_version="v1",
        )

    def test_teacher_release_samples_parse_heading_style(self):
        with tempfile.TemporaryDirectory() as temp:
            for name in ("teacher-standard", "teacher-bad-m3"):
                with self.subTest(fixture=name):
                    base = write_repository(
                        Path(temp) / name,
                        srs=TEACHER_STANDARD_SRS,
                        tests=TEACHER_STANDARD_TEST_FILES,
                    )
                    (base / "src").mkdir()
                    (base / "src" / "unrelated.py").write_text(
                        "VALUE = 1\n",
                        encoding="utf-8",
                    )
                    (base / "docs" / "m2-架构与设计").mkdir(parents=True)
                    (
                        base / "docs" / "m2-架构与设计" / "architecture.md"
                    ).write_text(
                        "# Unrelated content\n",
                        encoding="utf-8",
                    )
                    requirements = parse_srs_file(
                        base / "docs" / "m1-立项与需求" / "SRS.md"
                    )
                    cases = [
                        case
                        for path in sorted((base / "tests").glob("*.md"))
                        for case in parse_tests_file(path)
                    ]
                    self.assertEqual(6, len(requirements))
                    self.assertEqual(5, len(cases))
                    self.assertTrue(all(case.result == "UNKNOWN" for case in cases))
                    self.assertTrue(
                        next(
                            req for req in requirements if req.id == "FR-02"
                        ).critical
                    )

    def test_teacher_release_samples_report_required_b_rules(self):
        with tempfile.TemporaryDirectory() as temp:
            for name in ("teacher-standard", "teacher-bad-m3"):
                with self.subTest(fixture=name):
                    base = write_repository(
                        Path(temp) / name,
                        srs=TEACHER_STANDARD_SRS,
                        tests=TEACHER_STANDARD_TEST_FILES,
                    )
                    result = self._analyze(base)
                    self.assertIn("FR-05", result.refs_for("MISSING_TEST"))
                    self.assertIn(
                        "FR-02",
                        result.refs_for("CRITICAL_NO_BOUNDARY"),
                    )
                    self.assertIn("TC-22", result.refs_for("ORPHAN_TEST"))
                    for issue in result.issues:
                        self.assertTrue(issue.file)
                        self.assertGreaterEqual(issue.line, 1)

    def test_nonstructured_srs_produces_no_guessed_requirements(self):
        text = "系统应自动理解这段自然语言并推测需求关系。"
        self.assertEqual([], parse_srs_text(text, "nonstructured.md"))

    def test_nonstructured_input_enters_manual_path(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = write_repository(
                Path(temp) / "repo",
                srs="系统应自动推断所有需求与测试之间的关系。\n",
                tests="# TC-01 自然语言猜测（happy）\ncovers: FR-01\n",
            )
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = main([
                    "check",
                    str(repo),
                    "--output-dir",
                    str(Path(temp) / "reports"),
                    "--team-id",
                    "G99",
                ])
            self.assertEqual(1, code)
            self.assertIn("非结构化输入不得自动定稿", stderr.getvalue())
            self.assertFalse((Path(temp) / "reports").exists())


if __name__ == "__main__":
    unittest.main()
