# -*- coding: utf-8 -*-
import unittest
from pathlib import Path

from src.traceability.parser import (
    parse_srs_file,
    parse_srs_text,
    parse_tests_file,
    parse_tests_text,
)

ROOT = Path(__file__).resolve().parents[1]


class ParserTests(unittest.TestCase):
    def test_project_srs_parses_all_requirements(self):
        requirements = parse_srs_file(
            ROOT / "docs" / "m1-立项与需求" / "SRS.md"
        )
        self.assertEqual(14, len(requirements))
        self.assertTrue(all(req.line > 0 for req in requirements))
        self.assertEqual(
            {"FR-03", "FR-04", "FR-06", "FR-08", "FR-10"},
            {req.id for req in requirements if req.critical},
        )

    def test_project_tests_parse_all_cases_and_kinds(self):
        cases = [
            case
            for path in sorted((ROOT / "tests").glob("TC-*.md"))
            for case in parse_tests_file(path)
        ]
        self.assertEqual(21, len(cases))
        self.assertEqual(
            [f"TC-{index:02d}" for index in range(1, 22)],
            [case.id for case in cases],
        )
        self.assertTrue(all(case.result == "PASS" for case in cases))
        self.assertIn("happy", {case.kind for case in cases})
        self.assertIn("boundary", {case.kind for case in cases})
        self.assertIn("invalid", {case.kind for case in cases})
        self.assertEqual("FR-14", cases[-1].covers[0])
        self.assertEqual("v2", cases[-1].verified_version)

    def test_field_style_requirement_starts_at_line_one(self):
        text = (
            "FR-01 首行需求\n"
            "- 描述: 解析首行\n"
            "- 优先级: critical\n"
            "- 验收标准: 正确解析\n"
            "- 版本: v3\n"
        )
        requirement = parse_srs_text(text, "memory.md")[0]
        self.assertEqual(1, requirement.line)
        self.assertEqual("v3", requirement.version)
        self.assertTrue(requirement.critical)

    def test_multiple_covers_are_sorted(self):
        text = (
            "用例编号: TC-01\n"
            "covers: FR-03 / FR-01\n"
            "类型: 边界\n"
            "实际结果: PASS\n"
        )
        case = parse_tests_text(text)[0]
        self.assertEqual(("FR-01", "FR-03"), case.covers)
        self.assertEqual("boundary", case.kind)

    def test_result_requires_an_explicit_exact_value(self):
        cases = {
            "PASS": "PASS",
            "FAIL": "FAIL",
            "未执行": "UNKNOWN",
            "NOT PASS": "UNKNOWN",
            "FAIL（期望 PASS）": "UNKNOWN",
        }
        for raw, expected in cases.items():
            with self.subTest(result=raw):
                text = (
                    "用例编号: TC-01\n"
                    "covers: FR-01\n"
                    "类型: 正常\n"
                    f"实际结果: {raw}\n"
                )
                self.assertEqual(expected, parse_tests_text(text)[0].result)


if __name__ == "__main__":
    unittest.main()
