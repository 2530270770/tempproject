# -*- coding: utf-8 -*-
"""Measure source line coverage with Python's standard-library trace module."""

from __future__ import annotations

import dis
import io
import sys
import trace
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def executable_lines(code) -> set[int]:
    lines = {line for _, line in dis.findlinestarts(code) if line is not None}
    for constant in code.co_consts:
        if isinstance(constant, type(code)):
            lines.update(executable_lines(constant))
    return lines


def main() -> int:
    tracer = trace.Trace(
        count=True,
        trace=False,
        ignoredirs=[str(Path(__file__).parent)],
    )
    buffer = io.StringIO()

    def run_tests():
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
        return unittest.TextTestRunner(stream=buffer, verbosity=2).run(suite)

    result = tracer.runfunc(run_tests)
    print(buffer.getvalue())
    counts = tracer.results().counts
    covered_by_file: dict[Path, set[int]] = {}
    for (filename, line), count in counts.items():
        if count:
            covered_by_file.setdefault(Path(filename).resolve(), set()).add(line)

    total = 0
    hit = 0
    print("\nLine coverage (src):")
    for source in sorted((ROOT / "src").rglob("*.py")):
        code = compile(source.read_text(encoding="utf-8"), str(source), "exec")
        lines = executable_lines(code)
        covered = lines & covered_by_file.get(source.resolve(), set())
        total += len(lines)
        hit += len(covered)
        ratio = len(covered) / len(lines) if lines else 1.0
        print(
            f"  {source.relative_to(ROOT)}: "
            f"{ratio:.1%} ({len(covered)}/{len(lines)})"
        )
    overall = hit / total if total else 1.0
    print(f"TOTAL: {overall:.1%} ({hit}/{total})")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
