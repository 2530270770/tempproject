# -*- coding: utf-8 -*-
"""读取评阅配置与花名册。

阈值以 assessment.yml 为准，本文件不内置任何具体数值。
优先使用 PyYAML；未安装时使用内置的 YAML 子集解析器，保证零依赖可运行。
"""
import re
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def _strip_comment(line):
    quoted = False
    quote = None
    for index, char in enumerate(line):
        if char in ("'", '"'):
            if not quoted:
                quoted, quote = True, char
            elif quote == char:
                quoted = False
        if char == "#" and not quoted:
            return line[:index].rstrip()
    return line.rstrip()


def _scalar(value):
    value = value.strip()
    if not value:
        return None
    if (
        (value.startswith('"') and value.endswith('"'))
        or (value.startswith("'") and value.endswith("'"))
    ):
        return value[1:-1]
    lowered = value.lower()
    if lowered in ("true", "yes"):
        return True
    if lowered in ("false", "no"):
        return False
    if lowered in ("null", "~"):
        return None
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    if value.startswith("{") and value.endswith("}"):
        inside = value[1:-1].strip()
        result = {}
        if not inside:
            return result
        for pair in inside.split(","):
            key, separator, raw = pair.partition(":")
            if not separator:
                raise ValueError("内联映射必须使用 key: value")
            result[key.strip()] = _scalar(raw)
        return result
    if value.startswith("[") and value.endswith("]"):
        inside = value[1:-1].strip()
        return [] if not inside else [_scalar(item) for item in inside.split(",")]
    return value


def _yaml_subset(text):
    """Parse the mappings/lists/scalars used by the course contract files."""

    raw_lines = []
    for original in text.splitlines():
        line = _strip_comment(original)
        if not line.strip() or line.strip() == "---":
            continue
        indent = len(line) - len(line.lstrip(" "))
        raw_lines.append((indent, line[indent:]))
    if not raw_lines:
        return {}

    def parse_block(index, indent):
        is_list = raw_lines[index][1].startswith("- ")
        container = [] if is_list else {}
        while index < len(raw_lines):
            current_indent, content = raw_lines[index]
            if current_indent < indent:
                break
            if current_indent > indent:
                raise ValueError(f"无法解析 YAML 缩进：{content}")
            if is_list:
                if not content.startswith("- "):
                    break
                rest = content[2:].strip()
                if ":" not in rest:
                    container.append(_scalar(rest))
                    index += 1
                    continue
                key, _, raw_value = rest.partition(":")
                item = {key.strip(): _scalar(raw_value)}
                index += 1
                if index < len(raw_lines) and raw_lines[index][0] > indent:
                    nested_indent = raw_lines[index][0]
                    nested, index = parse_block(index, nested_indent)
                    if isinstance(nested, dict):
                        item.update(nested)
                    else:
                        item[key.strip()] = nested
                container.append(item)
            else:
                if content.startswith("- "):
                    break
                key, separator, raw_value = content.partition(":")
                if not separator:
                    raise ValueError(f"YAML 行缺少冒号：{content}")
                key = key.strip()
                raw_value = raw_value.strip()
                index += 1
                if raw_value:
                    container[key] = _scalar(raw_value)
                elif index < len(raw_lines) and raw_lines[index][0] > indent:
                    nested_indent = raw_lines[index][0]
                    container[key], index = parse_block(index, nested_indent)
                else:
                    container[key] = None
        return container, index

    result, consumed = parse_block(0, raw_lines[0][0])
    if consumed != len(raw_lines):
        raise ValueError("YAML 仍有未解析内容")
    return result


def load_yaml(path):
    """读取任意 YAML 文件并返回字典。"""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if yaml is not None:
        return yaml.safe_load(text)
    return _yaml_subset(text)


def load_assessment(path="assessment.yml"):
    """返回评阅配置；校验里程碑与权重两段必须存在。"""
    data = load_yaml(path) or {}
    for key in ("milestones", "weights"):
        if key not in data:
            raise ValueError(f"assessment.yml 缺少必填段：{key}")
    return data


def load_roster(path="team-roster.yml"):
    """返回 (team_id, project, roster_dict)。"""
    data = load_yaml(path) or {}
    team = data.get("team", {})
    if not team.get("members"):
        raise ValueError("花名册 team.members 为空或不存在")
    return team.get("id"), team.get("project"), data


def threshold_for_project(assessment, project):
    """按选题返回对应阈值段：A->process，B->traceability，C->ai。"""
    mapping = {
        "A": "process_thresholds",
        "B": "traceability_thresholds",
        "C": "ai_thresholds",
    }
    return assessment.get(mapping.get(project, ""), {}) or {}
