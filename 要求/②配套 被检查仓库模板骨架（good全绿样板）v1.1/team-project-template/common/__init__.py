# -*- coding: utf-8 -*-
"""综合项目公共脚手架（与业务无关的通用底座）。

- repo.py：只读克隆、只读 git 命令封装（绝不 push）
- config.py：读取 assessment.yml / team-roster.yml，按选题取阈值
- report.py：统一报告 JSON 基类（Issue / ReportBuilder）

注意：本脚手架不包含“执行被测仓库构建/测试”的能力（本项目不依赖 CI Runner）。
核心检查规则（问题码、阈值判定、状态机）由各组自行实现。
"""
from .config import load_yaml, load_assessment, load_roster, threshold_for_project
from .repo import readonly_clone, run_git
from .report import Issue, ReportBuilder, Severity

__all__ = [
    "load_yaml", "load_assessment", "load_roster", "threshold_for_project",
    "readonly_clone", "run_git",
    "Issue", "ReportBuilder", "Severity",
]
