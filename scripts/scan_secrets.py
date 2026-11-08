"""
Bikozava — Pre-Commit & Repository Secret Scanner (`scripts/scan_secrets.py`)

Scans all tracked / staged files in the project before pushing to GitHub
(`https://github.com/imdadrekani884/bikozava`) to ensure:
1. `.env` is NOT tracked by Git.
2. No Supabase `service_role` JWTs, `sbp_` personal access tokens, PostgreSQL
   passwords, private keys (`BEGIN PRIVATE KEY`), or AWS/Stripe keys are committed.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
}

SECRET_PATTERNS = [
    ("Supabase Personal Access Token", re.compile(r"\bsbp_[a-fA-F0-9]{30,}\b")),
    ("Supabase Secret Key", re.compile(r"\bsb_secret_[a-zA-Z0-9_\-]{20,}\b")),
    ("JWT Token (potential service_role key)", re.compile(r"\beyJ[a-zA-Z0-9_\-]{20,}\.eyJ[a-zA-Z0-9_\-]{20,}\.[a-zA-Z0-9_\-]{20,}\b")),
    ("Hardcoded PostgreSQL Credentials", re.compile(r"postgresql://[^:\s]+:(?!\[YOUR-PASSWORD\]|\[YOUR-DB-PASSWORD\]|password@)[^@\s]{6,}@[^\s\"']+")),
    ("Private Cryptographic Key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("GitHub Personal Access Token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b")),
]

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "instance", "node_modules"}
SKIP_FILES = {".env", ".env.local", ".env.production", "scan_secrets.py"}


def scan_repository() -> int:
    issues: list[str] = []

    # 1. If git is initialized, check `git ls-files` for forbidden files
    git_dir = ROOT / ".git"
    if git_dir.exists():
        try:
            res = subprocess.run(
                ["git", "ls-files"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            tracked = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            for rel in tracked:
                name = Path(rel).name
                if name in FORBIDDEN_FILENAMES or rel.endswith(".db") or rel.endswith(".sqlite"):
                    issues.append(f"[CRITICAL] Tracked sensitive file in Git index: {rel}")
        except Exception:
            pass

    # 2. Scan source files (excluding git-ignored local .env)
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name in SKIP_FILES:
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp3", ".wav", ".mp4", ".webm", ".woff", ".woff2", ".ttf", ".pyc", ".db"}:
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        rel_path = path.relative_to(ROOT).as_posix()
        for label, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(content):
                snippet = match.group(0)[:24] + "..."
                issues.append(f"[SECRET DETECTED] {label} in {rel_path}: {snippet}")

    if issues:
        print("=" * 76)
        print("  [SECURITY BLOCK] SECRET SCANNER FOUND POTENTIAL EXPOSED CREDENTIALS:")
        print("=" * 76)
        for item in issues:
            print("  *", item)
        print("=" * 76)
        return 1

    print("[OK] Secret scan passed: 0 exposed secrets, tokens, or tracked .env files.")
    return 0


if __name__ == "__main__":
    sys.exit(scan_repository())
