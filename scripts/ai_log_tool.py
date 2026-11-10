# -*- coding: utf-8 -*-
"""Append and verify the course AI log without rewriting historical rows."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "process" / "ai-log.csv"
CHAIN_PATH = ROOT / "process" / "ai-log-hash-chain.csv"
FIELDS = [
    "date", "phase", "tool", "prompt", "artifact", "commit",
    "reviewer", "ai_decision", "human_action", "owner",
]
CHAIN_FIELDS = ["entry", "prev_hash", "entry_hash"]
GENESIS = "0" * 64


def canonical(row: dict[str, str]) -> bytes:
    return json.dumps(
        {field: row.get(field, "") for field in FIELDS},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def rows() -> list[dict[str, str]]:
    with LOG_PATH.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"ai-log.csv 表头必须严格为：{','.join(FIELDS)}")
        return list(reader)


def chain_records() -> list[dict[str, str]]:
    previous = GENESIS
    ledger = []
    for index, row in enumerate(rows(), start=1):
        digest = hashlib.sha256(previous.encode("ascii") + b"\n" + canonical(row)).hexdigest()
        ledger.append({
            "entry": str(index),
            "prev_hash": previous,
            "entry_hash": digest,
        })
        previous = digest
    return ledger


def rebuild_chain() -> None:
    ledger = chain_records()
    with CHAIN_PATH.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CHAIN_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(ledger)


def verify() -> list[str]:
    if not CHAIN_PATH.exists():
        return ["缺少 ai-log-hash-chain.csv"]
    with CHAIN_PATH.open("r", encoding="utf-8-sig", newline="") as stream:
        ledger = list(csv.DictReader(stream))
    entries = rows()
    failures = []
    if len(ledger) != len(entries):
        failures.append(f"日志有 {len(entries)} 行但哈希链有 {len(ledger)} 行")
    previous = GENESIS
    for index, (row, record) in enumerate(zip(entries, ledger), start=1):
        if record.get("entry") != str(index):
            failures.append(f"第 {index} 行序号不连续")
        if record.get("prev_hash") != previous:
            failures.append(f"第 {index} 行前序哈希不匹配")
        digest = hashlib.sha256(previous.encode("ascii") + b"\n" + canonical(row)).hexdigest()
        if record.get("entry_hash") != digest:
            failures.append(f"第 {index} 行内容哈希不匹配")
        previous = record.get("entry_hash", "")
    return failures


def append(values: dict[str, str]) -> None:
    failures = verify()
    if failures:
        raise ValueError("现有哈希链已损坏，拒绝追加：" + "；".join(failures))
    if not LOG_PATH.read_bytes().endswith(b"\n"):
        raise ValueError("ai-log.csv 末尾必须有换行")
    with LOG_PATH.open("a", encoding="utf-8", newline="") as stream:
        csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n").writerow(values)
    rebuild_chain()


def main() -> int:
    parser = argparse.ArgumentParser(description="AI 日志哈希链工具")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify", help="校验哈希链")
    sub.add_parser("rebuild", help="仅在初始化时重建哈希链")
    sub.add_parser("print-chain", help="只输出当前日志应生成的哈希链")
    add = sub.add_parser("append", help="追加一条经过人工审查的日志")
    for field in FIELDS:
        add.add_argument(f"--{field}", default="")
    args = parser.parse_args()
    if args.command == "verify":
        failures = verify()
        if failures:
            print("哈希链校验失败：" + "；".join(failures))
            return 1
        print(f"哈希链校验通过，共 {len(rows())} 条")
        return 0
    if args.command == "rebuild":
        rebuild_chain()
        print(f"已重建 {len(rows())} 条哈希记录")
        return 0
    if args.command == "print-chain":
        writer = csv.DictWriter(__import__("sys").stdout, fieldnames=CHAIN_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(chain_records())
        return 0
    values = {field: getattr(args, field) for field in FIELDS}
    missing = [field for field in FIELDS if field not in ("commit",) and not values[field]]
    if missing:
        print("缺少字段：" + "、".join(missing))
        return 1
    append(values)
    print("已追加并更新哈希链")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
