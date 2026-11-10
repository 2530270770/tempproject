# -*- coding: utf-8 -*-
import unittest

from tests import (
    BAD_SRS,
    BAD_TESTS,
    GOOD_SRS,
    GOOD_TESTS,
    REGRESSION_BASELINE_SRS,
    REGRESSION_CURRENT_SRS,
    REGRESSION_TESTS,
)
from src.traceability.engine import TraceabilityEngine
from src.traceability.parser import parse_srs_text, parse_tests_text


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = TraceabilityEngine()

    def test_good_fixture_has_no_issues(self):
        result = self.engine.analyze(
            parse_srs_text(GOOD_SRS),
            parse_tests_text(GOOD_TESTS),
            current_version="v1",
        )
        self.assertEqual([], result.issues)
        self.assertEqual(1.0, result.coverage["fr"])
        self.assertEqual("BASELINE_NOT_PROVIDED", result.regression["status"])

    def test_bad_fixture_reports_required_r3_and_r4(self):
        result = self.engine.analyze(
            parse_srs_text(BAD_SRS),
            parse_tests_text(BAD_TESTS),
            current_version="v1",
        )
        self.assertIn("FR-05", result.refs_for("MISSING_TEST"))
        self.assertIn("FR-02", result.refs_for("CRITICAL_NO_BOUNDARY"))
        self.assertIn("TC-22", result.refs_for("ORPHAN_TEST"))
        self.assertNotIn("FR-02", result.refs_for("CRITICAL_NO_HAPPY"))

    def test_all_fail_is_not_covered(self):
        requirements = parse_srs_text(
            "| 编号 | 需求描述 | 优先级 | 验收标准 |\n"
            "| --- | --- | --- | --- |\n"
            "| FR-01 | 功能 | 必做 | 成功 |\n"
        )
        tests = parse_tests_text(
            "用例编号: TC-01\ncovers: FR-01\n类型: 正常\n实际结果: FAIL\n"
        )
        result = self.engine.analyze(requirements, tests, current_version="v1")
        self.assertIn("FR-01", result.requirements_summary["uncovered"])
        self.assertIn("FR-01", result.refs_for("TEST_ALL_FAIL_MARKED_COVERED"))

    def test_unknown_result_is_not_reported_as_all_fail(self):
        requirements = parse_srs_text(
            "| 编号 | 需求描述 | 优先级 | 验收标准 |\n"
            "| --- | --- | --- | --- |\n"
            "| FR-01 | 功能 | 必做 | 成功 |\n"
        )
        tests = parse_tests_text(
            "用例编号: TC-01\n"
            "covers: FR-01\n"
            "类型: 正常\n"
            "实际结果: 未执行\n"
        )
        result = self.engine.analyze(requirements, tests, current_version="v1")
        self.assertIn("FR-01", result.refs_for("MISSING_TEST"))
        self.assertNotIn(
            "FR-01",
            result.refs_for("TEST_ALL_FAIL_MARKED_COVERED"),
        )

    def test_duplicate_and_bad_reference_codes(self):
        requirements = parse_srs_text(
            "| 编号 | 需求描述 | 优先级 | 验收标准 |\n"
            "| --- | --- | --- | --- |\n"
            "| FR-01 | 甲 | 必做 | 成功 |\n"
            "| FR-01 | 乙 | 必做 | 成功 |\n"
        )
        tests = parse_tests_text(
            "用例编号: TC-01\ncovers:\n类型: 正常\n实际结果: PASS\n\n"
            "用例编号: TC-02\ncovers: FR-01\n类型: 正常\n步骤: 同内容\n实际结果: PASS\n\n"
            "用例编号: TC-03\ncovers: FR-01\n类型: 正常\n步骤: 同内容\n实际结果: PASS\n"
        )
        result = self.engine.analyze(requirements, tests, current_version="v1")
        self.assertTrue(result.has_code("DUP_ID"))
        self.assertTrue(result.has_code("BAD_REF"))
        self.assertTrue(result.has_code("DUP_TEST"))

    def test_partially_invalid_cover_expression_reports_bad_ref(self):
        requirements = parse_srs_text(
            "| 编号 | 需求描述 | 优先级 | 验收标准 |\n"
            "| --- | --- | --- | --- |\n"
            "| FR-01 | 功能 | 必做 | 成功 |\n"
        )
        for cover in ("FR-01 / INVALID", "FR-01 / FR99", "FR-01 / FR-1"):
            with self.subTest(cover=cover):
                tests = parse_tests_text(
                    "用例编号: TC-01\n"
                    f"covers: {cover}\n"
                    "类型: 正常\n"
                    "实际结果: PASS\n"
                )
                result = self.engine.analyze(
                    requirements,
                    tests,
                    current_version="v1",
                )
                self.assertIn("TC-01", result.refs_for("BAD_REF"))

    def test_missing_happy_and_boundary_are_distinct(self):
        requirements = parse_srs_text(
            "| 编号 | 需求描述 | 优先级 | 验收标准 |\n"
            "| --- | --- | --- | --- |\n"
            "| FR-01 | 功能 | critical | 成功 |\n"
        )
        boundary_only = parse_tests_text(
            "用例编号: TC-01\ncovers: FR-01\n类型: 边界\n实际结果: PASS\n"
        )
        result = self.engine.analyze(
            requirements,
            boundary_only,
            current_version="v1",
        )
        self.assertEqual(["FR-01"], result.refs_for("CRITICAL_NO_HAPPY"))
        self.assertEqual([], result.refs_for("CRITICAL_NO_BOUNDARY"))

    def test_regression_marks_changed_and_pending_tests(self):
        result = self.engine.analyze(
            parse_srs_text(REGRESSION_CURRENT_SRS),
            parse_tests_text(REGRESSION_TESTS),
            baseline=parse_srs_text(REGRESSION_BASELINE_SRS),
            current_version="v2",
        )
        self.assertEqual(["FR-01", "FR-02"], result.regression["changed_fr"])
        self.assertEqual(["TC-01", "TC-02"], result.regression["affected_tests"])
        self.assertEqual(["TC-01", "TC-02"], result.regression["pending"])
        self.assertEqual("NEED_REGRESSION", result.regression["status"])

    def test_every_issue_has_locatable_evidence(self):
        result = self.engine.analyze(
            parse_srs_text(BAD_SRS, "SRS.md"),
            parse_tests_text(BAD_TESTS, "TC.md"),
            current_version="v1",
        )
        for issue in result.issues:
            self.assertTrue(issue.ref)
            self.assertTrue(issue.file)
            self.assertGreaterEqual(issue.line, 1)
            self.assertIn(":", f"{issue.file}:{issue.line}")


if __name__ == "__main__":
    unittest.main()
