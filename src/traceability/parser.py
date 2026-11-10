# -*- coding: utf-8 -*-
"""解析仓库统一结构化 Markdown 契约的确定性解析器。"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .models import Requirement, TestCase

FR_ID = re.compile(r"\bFR-\d{2,}\b")
TC_ID = re.compile(r"\bTC-\d{2,}\b")


def _read_text(path: str | Path) -> str:
    raw = Path(path).read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"无法解码文件：{path}")


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _digest(*parts: str) -> str:
    payload = "\x1f".join(_norm(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _clean_cell(value: str) -> str:
    value = value.strip().strip("|").strip()
    value = value.replace("**", "").replace("`", "")
    return _norm(value)


def _split_table_row(line: str) -> list[str]:
    return [_clean_cell(cell) for cell in line.strip().strip("|").split("|")]


def _column_map(header: list[str]) -> dict[str, int]:
    aliases: dict[str, tuple[str, ...]] = {
        "id": ("编号", "需求编号", "id"),
        "title": ("标题", "名称", "title"),
        "description": ("需求描述", "描述", "description"),
        "acceptance": ("验收标准", "验收条件", "acceptance"),
        "priority": ("优先级", "priority"),
        "version": ("版本", "version"),
    }
    result: dict[str, int] = {}
    for key, names in aliases.items():
        for index, cell in enumerate(header):
            if any(name.lower() in cell.lower() for name in names):
                result[key] = index
                break
    return result


def _looks_like_separator(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in cells)


def srs_version_from_text(text: str, default: str = "v1") -> str:
    match = re.search(
        r"(?im)^\s*(?:SRS\s*)?版本\s*[:：]\s*([^\s|]+)",
        text,
    )
    return match.group(1).strip() if match else default


def _requirement(
    req_id: str,
    *,
    title: str,
    description: str,
    acceptance: str,
    priority: str,
    version: str,
    source: str,
    line: int,
) -> Requirement:
    priority_text = _norm(priority)
    title_lower = title.lower()
    critical = (
        "critical" in priority_text.lower()
        or "关键" in priority_text
        or bool(re.search(r"(?:【critical】|\[critical\]|^\s*critical\b)", title_lower))
    )
    description_text = _norm(description)
    title_text = _norm(title) or description_text[:80]
    acceptance_text = _norm(acceptance)
    fingerprint = _digest(title_text, description_text, acceptance_text, priority_text)
    return Requirement(
        id=req_id,
        title=title_text,
        description=description_text,
        acceptance=acceptance_text,
        priority=priority_text or ("critical" if critical else "必做"),
        version=_norm(version),
        critical=critical,
        file=source,
        line=line,
        fingerprint=fingerprint,
    )


def parse_srs_text(text: str, source: str = "<memory>", default_version: str = "v1") -> list[Requirement]:
    """Parse both contract tables and field-style requirement blocks."""

    lines = text.splitlines()
    doc_version = srs_version_from_text(text, default_version)
    requirements: list[Requirement] = []
    table_ids: set[str] = set()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip().startswith("|"):
            index += 1
            continue
        header = _split_table_row(line)
        if index + 1 >= len(lines) or not _looks_like_separator(_split_table_row(lines[index + 1])):
            index += 1
            continue
        columns = _column_map(header)
        row_index = index + 2
        while row_index < len(lines) and lines[row_index].strip().startswith("|"):
            cells = _split_table_row(lines[row_index])
            if cells and FR_ID.fullmatch(cells[0]):
                def get(name: str, fallback: int | None = None) -> str:
                    position = columns.get(name)
                    if position is None:
                        position = fallback
                    return cells[position] if position is not None and position < len(cells) else ""

                description = get("description", 1)
                title = get("title", 0)
                if title == get("id", 0):
                    title = description
                requirement = _requirement(
                    cells[0],
                    title=title,
                    description=description,
                    acceptance=get("acceptance", 3),
                    priority=get("priority", 2),
                    version=get("version", None) or doc_version,
                    source=source,
                    line=row_index + 1,
                )
                requirements.append(requirement)
                table_ids.add(requirement.id)
            row_index += 1
        index = max(index + 2, row_index)

    block_start = re.compile(
        r"^\s*(?:[-*]\s*)?(?:#{1,6}\s*)?(?:\*\*)?"
        r"(FR-\d{2,})(?:\*\*)?\s*[:：\-]?\s*(.*)$",
        re.IGNORECASE,
    )
    for idx, line in enumerate(lines):
        match = block_start.match(line)
        if not match or match.group(1) in table_ids:
            continue
        req_id = match.group(1)
        title = _clean_cell(match.group(2))
        fields: dict[str, str] = {}
        cursor = idx + 1
        while cursor < len(lines):
            candidate = lines[cursor]
            if block_start.match(candidate) or re.match(r"^\s*#{1,3}\s+", candidate):
                break
            field_match = re.match(
                r"^\s*[-*]?\s*(需求描述|描述|优先级|验收标准|版本)\s*[:：]\s*(.+)$",
                candidate,
            )
            if field_match:
                fields[field_match.group(1)] = _clean_cell(field_match.group(2))
            cursor += 1
        description = fields.get("需求描述") or fields.get("描述") or title
        requirements.append(
            _requirement(
                req_id,
                title=title,
                description=description,
                acceptance=fields.get("验收标准", ""),
                priority=fields.get("优先级", ""),
                version=fields.get("版本", doc_version),
                source=source,
                line=idx + 1,
            )
        )
    return sorted(requirements, key=lambda item: (item.id, item.line))


def parse_srs_file(path: str | Path, default_version: str = "v1") -> list[Requirement]:
    return parse_srs_text(_read_text(path), str(path), default_version)


def _kind(value: str) -> str:
    value = _norm(value).lower()
    if any(token in value for token in ("边界", "boundary")):
        return "boundary"
    if any(token in value for token in ("无效", "异常", "negative", "invalid")):
        return "invalid"
    if any(token in value for token in ("正常", "主成功", "happy", "normal")):
        return "happy"
    return "other"


def _result(value: str) -> str:
    value = _norm(value).upper()
    if value in {"PASS", "PASSED", "通过", "已通过"}:
        return "PASS"
    if value in {"FAIL", "FAILED", "失败", "未通过"}:
        return "FAIL"
    return "UNKNOWN"


def _covers(value: str) -> tuple[str, ...]:
    return tuple(sorted(set(FR_ID.findall(value or ""))))


def covers_syntax_valid(value: str) -> bool:
    """Return whether every covers token is a complete FR-xx identifier."""
    normalized = _norm(value)
    if normalized.startswith("[") and normalized.endswith("]"):
        normalized = normalized[1:-1].strip()
    tokens = [
        token
        for token in re.split(r"[,，、/;；\s]+", normalized)
        if token
    ]
    return bool(tokens) and all(FR_ID.fullmatch(token) for token in tokens)


def _field(block: str, names: tuple[str, ...]) -> str:
    joined = "|".join(re.escape(name) for name in names)
    match = re.search(rf"(?im)^\s*[-*]?\s*(?:{joined})\s*[:：]\s*(.+?)\s*$", block)
    return _clean_cell(match.group(1)) if match else ""


def _testcase(
    test_id: str,
    body: str,
    source: str,
    line: int,
    fields: dict[str, str] | None = None,
) -> TestCase:
    values = fields or {}
    lines = body.splitlines()
    first_line = lines[0] if lines else ""
    heading_style = bool(
        re.match(r"^\s*#{1,6}\s*(?:\*\*)?TC-\d{2,}\b", first_line, re.IGNORECASE)
    )
    cover_raw = values.get("covers") or _field(body, ("covers", "覆盖需求", "覆盖"))
    kind_raw = values.get("kind") or _field(body, ("类型", "case_type", "type"))
    if not kind_raw and heading_style:
        kind_raw = first_line
    result_raw = values.get("result") or _field(body, ("实际结果", "结果", "result"))
    verified = values.get("verified") or _field(
        body,
        ("验证需求版本", "验证版本", "verified_srs_version"),
    )
    covers = _covers(cover_raw)
    semantic_body = re.sub(
        r"(?im)^\s*用例编号\s*[:：]\s*TC-\d{2,}\s*$",
        "用例编号:",
        body,
    )
    semantic_body = re.sub(
        r"(?im)^\s*#{1,6}\s*TC-\d{2,}.*$",
        "TC:",
        semantic_body,
    )
    kind = _kind(kind_raw)
    result = _result(result_raw)
    fingerprint = _digest(kind_raw, cover_raw, semantic_body)
    return TestCase(
        id=test_id,
        covers=covers,
        cover_raw=_norm(cover_raw),
        kind=kind,
        result=result,
        verified_version=_norm(verified),
        body=_norm(body),
        file=source,
        line=line,
        fingerprint=fingerprint,
    )


def _find_case_starts(lines: list[str]) -> list[tuple[int, str]]:
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        heading_match = re.match(
            r"^\s*#{1,6}\s*(?:\*\*)?(TC-\d{2,})\b",
            line,
            re.IGNORECASE,
        )
        if heading_match:
            starts.append((index, heading_match.group(1)))
            continue
        if not re.search(r"(?:用例编号|测试用例编号|test\s*id)\s*[:：]?", line, re.IGNORECASE):
            continue
        match = TC_ID.search(line)
        if match:
            starts.append((index, match.group(0)))
    return starts


def parse_tests_text(text: str, source: str = "<memory>") -> list[TestCase]:
    lines = text.splitlines()
    starts = _find_case_starts(lines)
    tests: list[TestCase] = []
    for position, (start, test_id) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        tests.append(_testcase(test_id, "\n".join(lines[start:end]), source, start + 1))
    return tests


def parse_tests_file(path: str | Path) -> list[TestCase]:
    return parse_tests_text(_read_text(path), str(path))
