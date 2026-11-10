# -*- coding: utf-8 -*-
"""供命令行边界使用的轻量角色权限策略。"""

from __future__ import annotations


class PermissionDenied(PermissionError):
    pass


_ALLOWED = {
    "teacher": {"run_check", "view_all", "confirm", "configure"},
    "ta": {"run_check", "view_all", "confirm"},
    "student": {"view_current_team"},
}


def authorize(
    role: str,
    action: str,
    *,
    caller_team: str | None = None,
    target_team: str | None = None,
) -> None:
    role_key = (role or "").strip().lower()
    allowed = _ALLOWED.get(role_key)
    if allowed is None:
        raise PermissionDenied(f"未知角色：{role}")
    if action not in allowed:
        raise PermissionDenied(f"角色 {role_key} 无权执行 {action}")
    if role_key == "student" and action == "view_current_team":
        if not caller_team or caller_team != target_team:
            raise PermissionDenied("学生只能查看自己的组")
