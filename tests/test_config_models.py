# -*- coding: utf-8 -*-
import tempfile
import unittest
from pathlib import Path

from common.config import (
    _yaml_subset,
    load_assessment,
    load_roster,
    threshold_for_project,
)
from common.repo import run_git
from src.traceability.models import AnalysisResult, Issue, Requirement, TestCase


class ConfigTests(unittest.TestCase):
    def test_builtin_yaml_subset_parses_nested_roster(self):
        data = _yaml_subset(
            "team:\n"
            "  id: T01\n"
            "  project: B\n"
            "  members:\n"
            "    - name: 甲\n"
            "      gitlab: jia\n"
            "    - name: 乙\n"
            "      gitlab: yi\n"
        )
        self.assertEqual("T01", data["team"]["id"])
        self.assertEqual(["甲", "乙"], [m["name"] for m in data["team"]["members"]])

    def test_load_assessment_and_project_threshold(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "assessment.yml"
            path.write_text(
                "milestones: {}\n"
                "weights: {team: 70}\n"
                "traceability_thresholds:\n"
                "  min_cases_per_fr: 2\n",
                encoding="utf-8",
            )
            config = load_assessment(path)
            self.assertEqual(2, threshold_for_project(config, "B")["min_cases_per_fr"])

    def test_invalid_roster_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "team-roster.yml"
            path.write_text("team:\n  id: T01\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_roster(path)

    def test_run_git_rejects_potential_mutation_commands(self):
        for args in (
            ["branch", "-D", "main"],
            ["tag", "-d", "m2-architecture"],
            ["remote", "set-url", "origin", "https://example.invalid/repo"],
        ):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    run_git(".", args)


class ModelTests(unittest.TestCase):
    def _requirement(self, req_id="FR-01"):
        return Requirement(
            req_id, "标题", "描述", "验收", "必做", "v1", False,
            "SRS.md", 1, "hash",
        )

    def _test(self, test_id="TC-01", covers=("FR-01",)):
        return TestCase(
            test_id, covers, ",".join(covers), "happy", "PASS", "v1",
            "body", "TC.md", 1, "hash",
        )

    def test_issue_serialization_omits_empty_locators(self):
        self.assertEqual(
            {"code": "MISSING_TEST", "severity": "HIGH", "evidence": "证据"},
            Issue("MISSING_TEST", "HIGH", "证据").to_dict(),
        )

    def test_analysis_result_helpers(self):
        issues = [
            Issue("MISSING_TEST", "HIGH", "证据", ref="FR-01"),
            Issue("ORPHAN_TEST", "MEDIUM", "证据", ref="TC-99"),
        ]
        result = AnalysisResult(
            [self._requirement()],
            [self._test()],
            issues=issues,
        )
        self.assertTrue(result.has_code("MISSING_TEST"))
        self.assertFalse(result.has_code("DUP_ID"))
        self.assertEqual(["FR-01"], result.refs_for("MISSING_TEST"))


if __name__ == "__main__":
    unittest.main()
