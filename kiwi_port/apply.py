#!/usr/bin/env python3
"""Apply the pinned Kiwi UI core patch to a post-Titanium Chromium tree."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
PATCH = HERE / "kiwi-ui-core.patch"


def digest(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_git(source: Path, *args: str) -> None:
    completed = subprocess.run(
        ["git", "-C", str(source), *args], text=True, capture_output=True
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(detail or f"git {' '.join(args)} failed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="post-Titanium Chromium src directory")
    args = parser.parse_args()
    source = args.source.resolve()
    if not (source / ".git").exists():
        raise RuntimeError(f"not a Chromium git tree: {source}")

    states: dict[str, str] = {}
    for relative, expected in MANIFEST["files"].items():
        if relative.startswith("/") or ".." in Path(relative).parts:
            raise RuntimeError(f"unsafe manifest path: {relative}")
        actual = digest(source / relative)
        if actual == expected["after_sha256"]:
            states[relative] = "after"
        elif actual == expected["before_sha256"]:
            states[relative] = "before"
        else:
            states[relative] = "mismatch"

    mismatches = [path for path, state in states.items() if state == "mismatch"]
    if mismatches:
        joined = "\n  ".join(mismatches)
        raise RuntimeError(
            "source does not match the pinned post-Titanium baseline:\n  " + joined
        )

    if all(state == "after" for state in states.values()):
        print("Kiwi UI core patch is already applied.")
        return 0
    if not all(state == "before" for state in states.values()):
        mixed = [f"{path}: {state}" for path, state in states.items()]
        raise RuntimeError("partially applied source:\n  " + "\n  ".join(mixed))

    run_git(source, "apply", "--check", str(PATCH))
    run_git(source, "apply", str(PATCH))

    bad = [
        path
        for path, expected in MANIFEST["files"].items()
        if digest(source / path) != expected["after_sha256"]
    ]
    if bad:
        raise RuntimeError("post-apply verification failed: " + ", ".join(bad))

    print(f"Applied Kiwi UI core patch to {len(states)} files.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
