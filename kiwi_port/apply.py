#!/usr/bin/env python3
"""Apply feature-scoped Kiwi UI patches to a post-Titanium Chromium tree."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
SERIES = json.loads((HERE / "patches/series.json").read_text(encoding="utf-8"))


def digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def git(source: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(["git", "-C", str(source), *args], text=True, capture_output=True)
    if check and completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(detail or f"git {' '.join(args)} failed")
    return completed


def safe_relative(relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"unsafe patch path: {relative}")
    return path


def write_report(report: Path, source: Path, results: list[dict[str, object]]) -> None:
    report.parent.mkdir(parents=True, exist_ok=True)
    conflicts = [item for item in results if item["status"] == "conflict"]
    lines = [
        "# Kiwi patch reapplication report", "", f"Source: `{source}`", "",
        "| Feature | Status | Files requiring repair |", "|---|---|---|",
    ]
    for item in results:
        files = "<br>".join(f"`{path}`" for path in item.get("conflicts", [])) or "—"
        lines.append(f"| `{item['id']}` — {item['name']} | {item['status']} | {files} |")
    if conflicts:
        lines += ["", "Clean hunks and later independent features were applied. Rejected hunks are in the listed `.rej` files.", "Repair only those files, remove the `.rej` files, then regenerate the feature patches."]
    else:
        lines += ["", "All feature patches applied without conflicts."]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.with_suffix(".json").write_text(json.dumps({"source": str(source), "features": results}, indent=2) + "\n", encoding="utf-8")


def file_states(source: Path) -> dict[str, str]:
    states: dict[str, str] = {}
    for relative, expected in MANIFEST["files"].items():
        safe_relative(relative)
        actual = digest(source / relative)
        if actual == expected["after_sha256"]:
            states[relative] = "after"
        elif actual == expected["before_sha256"]:
            states[relative] = "before"
        else:
            states[relative] = "mismatch"
    return states


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="post-Titanium Chromium src directory")
    parser.add_argument("--best-effort", action="store_true", help="apply clean hunks/features and leave .rej files for upstream conflicts")
    parser.add_argument("--report", type=Path, help="write Markdown and JSON reports")
    args = parser.parse_args()
    source = args.source.resolve()
    if not (source / ".git").exists():
        raise RuntimeError(f"not a Chromium git tree: {source}")

    states = file_states(source)
    if all(state == "after" for state in states.values()):
        print("Kiwi UI feature patches are already applied.")
        if args.report:
            write_report(
                args.report.resolve(),
                source,
                [
                    {
                        "id": feature["id"],
                        "name": feature["name"],
                        "patch": feature["patch"],
                        "status": "already-applied",
                        "conflicts": [],
                    }
                    for feature in SERIES["features"]
                ],
            )
        return 0

    pinned_before = all(state == "before" for state in states.values())
    if not args.best_effort:
        # Preflight the complete series before changing any file. Feature
        # patches own disjoint files, so every contextual check can be done
        # against the same untouched tree.
        failures = []
        for feature in SERIES["features"]:
            patch = HERE / "patches" / safe_relative(feature["patch"])
            if digest(patch) != feature["sha256"]:
                raise RuntimeError(f"patch checksum mismatch: {patch.name}")
            forward = git(source, "apply", "--check", str(patch)).returncode == 0
            reverse = git(source, "apply", "--reverse", "--check", str(patch)).returncode == 0
            if not forward and not reverse:
                failures.append(feature)
        if failures:
            details = "\n".join(
                f"  {feature['id']} ({feature['name']}): " + ", ".join(feature["files"])
                for feature in failures
            )
            raise RuntimeError(
                "strict preflight failed; source was not changed:\n" + details
                + "\nrerun with --best-effort --report <path> to isolate conflicts"
            )

    results: list[dict[str, object]] = []
    for feature in SERIES["features"]:
        patch = HERE / "patches" / safe_relative(feature["patch"])
        if digest(patch) != feature["sha256"]:
            raise RuntimeError(f"patch checksum mismatch: {patch.name}")
        item: dict[str, object] = {"id": feature["id"], "name": feature["name"], "patch": feature["patch"], "status": "pending", "conflicts": []}
        if git(source, "apply", "--reverse", "--check", str(patch)).returncode == 0:
            item["status"] = "already-applied"
        elif git(source, "apply", "--check", str(patch)).returncode == 0:
            git(source, "apply", "--whitespace=nowarn", str(patch), check=True)
            item["status"] = "applied"
        elif not args.best_effort:
            files = "\n  ".join(feature["files"])
            raise RuntimeError(f"feature {feature['id']} ({feature['name']}) does not apply cleanly:\n  {files}\nrerun with --best-effort --report <path> to apply independent clean changes")
        else:
            git(source, "apply", "--reject", "--whitespace=nowarn", str(patch))
            rejected = [str(safe_relative(path)) for path in feature["files"] if (source / f"{path}.rej").is_file()]
            item["status"] = "conflict"
            item["conflicts"] = rejected or feature["files"]
        results.append(item)

    if args.report:
        write_report(args.report.resolve(), source, results)
    conflicts = [item for item in results if item["status"] == "conflict"]
    if conflicts:
        for item in conflicts:
            print(f"CONFLICT {item['id']} ({item['name']}): " + ", ".join(item["conflicts"]), file=sys.stderr)
        return 2
    if pinned_before:
        after = file_states(source)
        bad = [path for path, state in after.items() if state != "after"]
        if bad:
            raise RuntimeError("pinned post-apply verification failed: " + ", ".join(bad))
    print(f"Applied/verified {len(results)} Kiwi UI feature patches.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
