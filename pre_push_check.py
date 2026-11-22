#!/usr/bin/env python3
"""Safety/privacy checks to run before pushing this repository to GitHub.

Checks (all local, no network):
  1. Secrets/credentials in tracked files and commit messages.
  2. Personally identifying absolute home-directory paths / personal emails.
  3. Credentials embedded in the git remote URL.
  4. Oversized or game-data/binary files that must not be committed.
  5. Working tree cleanliness (untracked files may contain private data).
  6. Commit identity matches the configured git user (post-history-rewrite).

Allowlisted (per project decision): the username `shovas` and its GitHub
noreply email; placeholder paths such as `<home>`, `~/...`, `../...`.

Usage:  python3 pre_push_check.py [--allow-untracked]
Exit 0 = clean, 1 = issues found.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent

ALLOWED_EMAILS = {"shovas@users.noreply.github.com"}
ALLOWED_USERS = {"shovas"}

SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |OPENSSH |DSA |EC )?PRIVATE KEY-----"),
    "github token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    "github PAT": re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    "aws key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "openai key": re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    "secret assignment": re.compile(r"(?i)\b(?:api[_-]?key|password|passwd|secret[_-]?key|access[_-]?token)\s*[:=]\s*['\"][^'\"<>{}$]{8,}['\"]"),
    "bearer token": re.compile(r"\bBearer\s+[A-Za-z0-9._-]{16,}"),
}

HOME_PATH = re.compile(r"(?i)(?:/home|/Users|/home/users)/([A-Za-z0-9_.-]+)|[A-Z]:\\Users\\([A-Za-z0-9_.-]+)")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

GAME_DATA_EXT = {".gtr", ".gtl", ".mas", ".bmw", ".dds", ".gmt", ".bik", ".car", ".exe", ".dll", ".zip", ".7z", ".rar"}
MAX_TRACKED_BYTES = 2 * 1024 * 1024  # 2 MiB
# These files intentionally contain example secrets/PII as detection patterns.
EXCLUDE_FROM_CONTENT_SCAN = {"pre_push_check.py", "tests/test_pre_push_check.py"}


@dataclass
class Issue:
    kind: str
    where: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.kind}] {self.where}: {self.detail}"


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def scan_text(text: str, where: str) -> list[Issue]:
    """Scan a text blob for secrets and PII."""
    issues: list[Issue] = []
    for label, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            issues.append(Issue("SECRET", where, f"possible {label}"))
    for m in HOME_PATH.finditer(text):
        user = m.group(1) or m.group(2)
        if user and user.lower() not in ALLOWED_USERS:
            issues.append(Issue("PII", where, f"personal home path for user '{user}'"))
    for m in EMAIL.finditer(text):
        email = m.group(0).lower()
        if email not in ALLOWED_EMAILS and not email.endswith("@users.noreply.github.com"):
            issues.append(Issue("PII", where, f"email address '{email}'"))
    return issues


def check_repo(allow_untracked: bool = False) -> list[Issue]:
    issues: list[Issue] = []

    tracked = _git("ls-files").splitlines()
    for rel in tracked:
        path = ROOT / rel
        if not path.is_file():
            continue
        if path.stat().st_size > MAX_TRACKED_BYTES:
            issues.append(Issue("SIZE", rel, f"file exceeds {MAX_TRACKED_BYTES} bytes"))
        if path.suffix.lower() in GAME_DATA_EXT:
            issues.append(Issue("BINARY", rel, "game-data/binary file should not be committed"))
        if rel in EXCLUDE_FROM_CONTENT_SCAN:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary content scanned only by extension/size rules
        issues.extend(scan_text(text, rel))

    if not allow_untracked:
        untracked = [f for f in _git("ls-files", "--others", "--exclude-standard").splitlines() if f]
        if untracked:
            issues.append(Issue("UNTRACKED", ", ".join(untracked[:10]), "untracked files present (may contain private data)"))

    remote = _git("remote", "get-url", "origin")
    if re.search(r"https?://[^/@\s]+:[^@\s]+@", remote):
        issues.append(Issue("SECRET", "git remote origin", "credentials embedded in URL"))

    # Commit messages / identities.
    log = _git("log", "--format=%an <%ae> | %cn <%ce> | %s")
    issues.extend(scan_text(log, "git log"))
    name, email = _git("config", "user.name"), _git("config", "user.email")
    if name and email:
        expected = f"{name} <{email}>"
        identities = _git("log", "--format=%an <%ae>|%cn <%ce>").splitlines()
        bad = [line for line in identities if any(part.strip() != expected for part in line.split("|"))]
        if bad:
            issues.append(Issue("IDENTITY", "git log", f"{len(bad)} commit(s) do not match configured identity {expected}"))
    return issues


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--allow-untracked", action="store_true")
    args = ap.parse_args(argv)
    issues = check_repo(args.allow_untracked)
    if issues:
        print(f"FAIL: {len(issues)} issue(s) found:")
        for issue in issues:
            print(f"  {issue}")
        return 1
    print("PASS: no secrets, PII, oversized/game-data files, or identity issues found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
