# -*- coding: utf-8 -*-
"""需求—测试追溯一致性检查器（B 题）。"""

from .engine import TraceabilityEngine
from .models import AnalysisResult, Requirement, TestCase
from .parser import parse_srs_file, parse_srs_text, parse_tests_file

__all__ = [
    "AnalysisResult",
    "Requirement",
    "TestCase",
    "TraceabilityEngine",
    "parse_srs_file",
    "parse_srs_text",
    "parse_tests_file",
]
