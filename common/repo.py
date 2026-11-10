# -*- coding: utf-8 -*-
"""只读克隆与只读 git 命令封装。

纯标准库（调用系统 git），不依赖 GitPython；所有命令均为只读，绝不 push。
令牌只用于拼装 clone URL，不打印、不写日志、不落盘。
"""
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, quote

# 允许通过 run_git 执行的只读子命令（白名单）
READONLY_CMDS = {
    "log", "show", "diff", "cat-file", "rev-list", "rev-parse",
    "ls-tree", "blame", "shortlog", "for-each-ref", "describe",
}


def _inject_token(url, token):
    """把只读令牌放入 https URL，仅用于 clone。"""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not token:
        return url
    netloc = f"oauth2:{quote(token, safe='')}@{parts.netloc}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def readonly_clone(url, dest, token=None, ref=None, timeout=300, depth=None):
    """只读克隆到 dest；dest 已存在则先删除。失败抛异常，不做任何写回。"""
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    cmd = ["git", "clone", "--quiet"]
    if depth:
        cmd += ["--depth", str(depth)]
    cmd += [_inject_token(url, token), str(dest)]
    subprocess.run(cmd, check=True, timeout=timeout,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if ref:
        subprocess.run(["git", "-C", str(dest), "checkout", "--quiet", ref],
                       check=True, timeout=timeout)
    return dest


def run_git(cwd, args, timeout=60):
    """在 cwd 执行只读 git 命令并返回 stdout 文本；非白名单命令直接拒绝。"""
    if not args or args[0] not in READONLY_CMDS:
        raise ValueError(f"仅允许只读 git 命令，收到：{args[:1]}")
    proc = subprocess.run(
        ["git", "-C", str(cwd)] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=timeout, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip())
    return proc.stdout
