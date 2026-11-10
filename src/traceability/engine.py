# -*- coding: utf-8 -*-
"""追溯规则引擎与显式状态机编排。"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable

from .models import AnalysisResult, Issue, Requirement, TestCase
from .parser import covers_syntax_valid
from .state_machines import EntryMachine, RegressionMachine


class TraceabilityEngine:
    def __init__(
        self,
        *,
        min_cases_per_fr: int = 1,
        critical_requires_boundary: bool = True,
        critical_requires_happy: bool = True,
    ) -> None:
        self.min_cases_per_fr = max(1, int(min_cases_per_fr))
        self.critical_requires_boundary = bool(critical_requires_boundary)
        self.critical_requires_happy = bool(critical_requires_happy)

    @staticmethod
    def _issue(
        code: str,
        severity: str,
        evidence: str,
        *,
        ref: str | None = None,
        file: str | None = None,
        line: int | None = None,
    ) -> Issue:
        return Issue(code, severity, evidence, ref=ref, file=file, line=line)

    def analyze(
        self,
        requirements: Iterable[Requirement],
        tests: Iterable[TestCase],
        *,
        baseline: Iterable[Requirement] | None = None,
        current_version: str | None = None,
    ) -> AnalysisResult:
        reqs = sorted(list(requirements), key=lambda item: (item.id, item.line))
        cases = sorted(list(tests), key=lambda item: (item.id, item.file, item.line))
        issues: list[Issue] = []

        req_counts = Counter(req.id for req in reqs)
        test_counts = Counter(test.id for test in cases)
        for req_id, count in sorted(req_counts.items()):
            if count > 1:
                first = next(req for req in reqs if req.id == req_id)
                issues.append(self._issue(
                    "DUP_ID", "HIGH", f"需求编号 {req_id} 重复 {count} 次",
                    ref=req_id, file=first.file, line=first.line,
                ))
        for test_id, count in sorted(test_counts.items()):
            if count > 1:
                first = next(test for test in cases if test.id == test_id)
                issues.append(self._issue(
                    "DUP_ID", "HIGH", f"用例编号 {test_id} 重复 {count} 次",
                    ref=test_id, file=first.file, line=first.line,
                ))

        content_groups: dict[str, list[TestCase]] = defaultdict(list)
        for test in cases:
            content_groups[test.fingerprint].append(test)
        duplicate_tests: list[str] = []
        for group in content_groups.values():
            distinct_ids = sorted({test.id for test in group})
            if len(distinct_ids) > 1:
                duplicate_tests.extend(distinct_ids)
                first = group[0]
                issues.append(self._issue(
                    "DUP_TEST", "MEDIUM", f"用例内容重复：{'、'.join(distinct_ids)}",
                    ref=distinct_ids[0], file=first.file, line=first.line,
                ))

        req_map = {req.id: req for req in reqs}
        tests_by_fr: dict[str, list[TestCase]] = defaultdict(list)
        orphan: set[str] = set()
        for test in cases:
            if not covers_syntax_valid(test.cover_raw):
                issues.append(self._issue(
                    "BAD_REF", "HIGH",
                    f"{test.id} 的 covers 字段为空或包含非法 FR 编号",
                    ref=test.id, file=test.file, line=test.line,
                ))
            if not test.covers:
                continue
            for req_id in test.covers:
                if req_id not in req_map:
                    orphan.add(test.id)
                    issues.append(self._issue(
                        "ORPHAN_TEST", "MEDIUM",
                        f"{test.id} 引用不存在的需求 {req_id}",
                        ref=test.id, file=test.file, line=test.line,
                    ))
                else:
                    tests_by_fr[req_id].append(test)

        covered: set[str] = set()
        missing: set[str] = set()
        critical_no_boundary: set[str] = set()
        critical_no_happy: set[str] = set()
        all_fail: set[str] = set()
        entry_states: dict[str, str] = {}
        rtm_rows: list[dict[str, object]] = []

        for req in reqs:
            related = tests_by_fr.get(req.id, [])
            passing = [test for test in related if test.result == "PASS"]
            has_enough = len(passing) >= self.min_cases_per_fr
            has_boundary = any(test.kind == "boundary" for test in passing)
            has_happy = any(test.kind == "happy" for test in passing)

            machine = EntryMachine()
            machine.trigger("BASELINE")
            if has_enough:
                machine.trigger("COVER")
                covered.add(req.id)
            else:
                machine.trigger("UNCOVER")
                missing.add(req.id)

            if related and all(test.result == "FAIL" for test in related):
                all_fail.add(req.id)
                issues.append(self._issue(
                    "TEST_ALL_FAIL_MARKED_COVERED", "HIGH",
                    f"{req.id} 的关联用例均不为 PASS，不能计为已覆盖",
                    ref=req.id, file=req.file, line=req.line,
                ))
            if req.critical and self.critical_requires_boundary and not has_boundary:
                critical_no_boundary.add(req.id)
                issues.append(self._issue(
                    "CRITICAL_NO_BOUNDARY", "HIGH",
                    f"关键需求 {req.id} 缺少 PASS 的边界用例",
                    ref=req.id, file=req.file, line=req.line,
                ))
            if req.critical and self.critical_requires_happy and not has_happy:
                critical_no_happy.add(req.id)
                issues.append(self._issue(
                    "CRITICAL_NO_HAPPY", "HIGH",
                    f"关键需求 {req.id} 缺少 PASS 的正常用例",
                    ref=req.id, file=req.file, line=req.line,
                ))
            if req.id in missing:
                issues.append(self._issue(
                    "MISSING_TEST", "HIGH",
                    f"需求 {req.id} 没有达到阈值的 PASS 用例",
                    ref=req.id, file=req.file, line=req.line,
                ))

            entry_states[req.id] = machine.state
            rtm_rows.append({
                "requirement": req.id,
                "critical": req.critical,
                "tests": [test.id for test in related],
                "passing": [test.id for test in passing],
                "kinds": {
                    "happy": has_happy,
                    "boundary": has_boundary,
                    "invalid": any(test.kind == "invalid" for test in passing),
                },
                "status": "已覆盖" if has_enough else "未覆盖",
                "requirement_location": f"{req.file}:{req.line}",
            })

        regression = self._regression(
            reqs, cases,
            baseline=list(baseline) if baseline is not None else None,
            current_version=current_version,
            issues=issues,
            entry_states=entry_states,
        )

        unique_req_count = len(req_map)
        coverage_fr = len(covered) / unique_req_count if unique_req_count else 0.0
        critical = [req for req in req_map.values() if req.critical]
        critical_boundary = (
            sum(
                1 for req in critical
                if req.id not in critical_no_boundary
                and any(
                    test.kind == "boundary" and test.result == "PASS"
                    for test in tests_by_fr.get(req.id, [])
                )
            ) / len(critical)
            if critical else 1.0
        )
        critical_happy = (
            sum(
                1 for req in critical
                if req.id not in critical_no_happy
                and any(
                    test.kind == "happy" and test.result == "PASS"
                    for test in tests_by_fr.get(req.id, [])
                )
            ) / len(critical)
            if critical else 1.0
        )

        severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        issues.sort(key=lambda issue: (
            severity_order.get(issue.severity, 9),
            issue.code,
            issue.ref or "",
            issue.file or "",
            issue.line or 0,
        ))
        return AnalysisResult(
            requirements=reqs,
            tests=cases,
            issues=issues,
            rtm_rows=rtm_rows,
            requirements_summary={
                "total": unique_req_count,
                "covered": len(covered),
                "uncovered": sorted(missing),
                "critical_missing_boundary": sorted(critical_no_boundary),
                "critical_missing_happy": sorted(critical_no_happy),
            },
            tests_summary={
                "total": len(cases),
                "orphan": sorted(orphan),
                "duplicate": sorted(set(duplicate_tests) | {
                    test_id for test_id, count in test_counts.items() if count > 1
                }),
                "all_fail_marked_covered": sorted(all_fail),
            },
            coverage={
                "fr": round(coverage_fr, 4),
                "critical_boundary": round(critical_boundary, 4),
                "critical_happy": round(critical_happy, 4),
            },
            regression=regression,
            entry_states=entry_states,
        )

    def _regression(
        self,
        requirements: list[Requirement],
        tests: list[TestCase],
        *,
        baseline: list[Requirement] | None,
        current_version: str | None,
        issues: list[Issue],
        entry_states: dict[str, str],
    ) -> dict[str, object]:
        machine = RegressionMachine()
        if baseline is None:
            return {
                "changed_fr": [],
                "added_fr": [],
                "affected_tests": [],
                "pending": [],
                "missing_regression_evidence": [],
                "status": "BASELINE_NOT_PROVIDED",
                "state": machine.state,
                "history": [],
            }

        old = {req.id: req for req in baseline}
        new = {req.id: req for req in requirements}
        changed = sorted(
            req_id
            for req_id, req in old.items()
            if req_id not in new or new[req_id].fingerprint != req.fingerprint
        )
        added = sorted(req_id for req_id in new if req_id not in old)
        affected = sorted({
            test.id for test in tests
            if any(req_id in test.covers for req_id in changed)
        })
        pending: list[str] = []
        missing_regression_evidence: list[str] = []
        if changed:
            machine.trigger("DETECT_CHANGE")
            machine.trigger("ANALYZE")

            tests_by_changed_fr = {
                req_id: sorted({
                    test.id
                    for test in tests
                    if req_id in test.covers
                })
                for req_id in changed
            }
            missing_regression_evidence = sorted(
                req_id
                for req_id, related_ids in tests_by_changed_fr.items()
                if not related_ids
            )

            for test in tests:
                if test.id not in affected:
                    continue
                version_ok = (
                    current_version is not None
                    and test.verified_version == current_version
                )
                if test.result != "PASS" or not version_ok:
                    pending.append(test.id)
            pending = sorted(set(pending))

            needs_regression = bool(pending or missing_regression_evidence)
            machine.trigger("OPEN" if needs_regression else "CLOSE")

            for req_id in changed:
                related_ids = tests_by_changed_fr[req_id]
                req_pending = sorted(set(related_ids) & set(pending))
                if not related_ids:
                    detail = "缺少可回归证据"
                    severity = "HIGH"
                elif req_pending:
                    detail = f"待回归用例：{'、'.join(req_pending)}"
                    severity = "HIGH"
                else:
                    detail = "关联用例已通过且验证版本匹配"
                    severity = "LOW"

                issues.append(self._issue(
                    "NEED_REGRESSION",
                    severity,
                    f"{req_id} 相对基线已修改或删除；{detail}",
                    ref=req_id,
                    file=old[req_id].file,
                    line=old[req_id].line,
                ))
                entry_states[req_id] = "变更"
        return {
            "changed_fr": changed,
            "added_fr": added,
            "affected_tests": affected,
            "pending": pending,
            "missing_regression_evidence": missing_regression_evidence,
            "status": (
                "NEED_REGRESSION"
                if pending or missing_regression_evidence
                else "CLOSED"
            ),
            "state": machine.state,
            "history": machine.history,
        }
