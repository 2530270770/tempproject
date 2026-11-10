# -*- coding: utf-8 -*-
"""B 题契约要求的显式有限状态机。"""

from __future__ import annotations

from dataclasses import dataclass, field


class InvalidTransition(ValueError):
    pass


@dataclass
class StateMachine:
    name: str
    state: str
    transitions: dict[tuple[str, str], str]
    history: list[dict[str, str]] = field(default_factory=list)

    def trigger(self, event: str) -> str:
        key = (self.state, event)
        if key not in self.transitions:
            raise InvalidTransition(
                f"{self.name}: 不允许从 {self.state} 触发 {event}"
            )
        previous = self.state
        self.state = self.transitions[key]
        self.history.append({"from": previous, "event": event, "to": self.state})
        return self.state


class CheckTaskMachine(StateMachine):
    def __init__(self) -> None:
        super().__init__(
            name="检查任务",
            state="待解析",
            transitions={
                ("待解析", "PARSE"): "已结构化",
                ("已结构化", "CHECK"): "规则核对中",
                ("规则核对中", "REPORT"): "差异报告",
                ("差异报告", "CONFIRM"): "人工确认",
                ("人工确认", "ARCHIVE"): "已归档",
                ("待解析", "FAIL"): "异常待人工",
                ("已结构化", "FAIL"): "异常待人工",
                ("规则核对中", "FAIL"): "异常待人工",
                ("异常待人工", "RETRY"): "待解析",
            },
        )


class EntryMachine(StateMachine):
    def __init__(self) -> None:
        super().__init__(
            name="需求/用例条目",
            state="草稿",
            transitions={
                ("草稿", "BASELINE"): "已基线",
                ("已基线", "COVER"): "已覆盖",
                ("已基线", "UNCOVER"): "未覆盖",
                ("已覆盖", "CHANGE"): "变更",
                ("未覆盖", "CHANGE"): "变更",
                ("变更", "REBASELINE"): "已基线",
            },
        )


class RegressionMachine(StateMachine):
    def __init__(self) -> None:
        super().__init__(
            name="变更回归",
            state="已基线",
            transitions={
                ("已基线", "DETECT_CHANGE"): "检出FR变更",
                ("检出FR变更", "ANALYZE"): "影响分析",
                ("影响分析", "OPEN"): "待回归",
                ("影响分析", "CLOSE"): "回归完成",
                ("待回归", "REGRESSED"): "回归完成",
                ("回归完成", "NEW_BASELINE"): "已基线",
            },
        )
