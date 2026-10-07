"""Enforce changed-file complexity on Git snapshots."""

from __future__ import annotations

import argparse
import fnmatch
import io
import subprocess
import sys
import tempfile
import tokenize
from pathlib import Path

UNSUPPORTED = frozenset(["c", "cc", "cpp", "cxx", "cs", "go", "java", "js", "ts", "jsx", "tsx", "rb", "rs", "swift", "kt"])
ZERO = "0" * 40


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], stderr=subprocess.PIPE)


def paths(base: str | None, ref: str) -> list[str]:
    revisions = ["--cached"] if ref == ":" else [str(base), ref]
    output = git("diff", "--name-only", "-z", "--diff-filter=ACMR", *revisions)
    return [name.decode("utf-8", "surrogateescape") for name in output.split(b"\0") if name]


def blob(ref: str, path: str) -> bytes:
    return git("show", f"{ref}{path}" if ref == ":" else f"{ref}:{path}")


def manifest(ref: str) -> list[str]:
    path = "scripts/ccn-allow-manifest.txt"
    files = git("ls-files", "-z") if ref == ":" else git("ls-tree", "-rz", "--name-only", ref)
    if path.encode() not in files.split(b"\0"):
        return []
    return [line.strip() for line in blob(ref, path).decode().splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def check_analyzer() -> None:
    result = subprocess.run([sys.executable, "-m", "lizard", "--version"],
                            capture_output=True, text=True, check=False)
    version = (result.stdout + result.stderr).strip()
    if result.returncode or version != "1.24.0":
        raise ValueError(f"lizard==1.24.0 required; got {version!r}")


def validate_paths(files: list[str]) -> None:
    unsupported = [path for path in files if path.rsplit(".", 1)[-1] in UNSUPPORTED]
    if unsupported:
        raise ValueError(f"unsupported imperative languages: {unsupported!r}")


def reject_suppression(content: bytes, path: str) -> None:
    tokens = tokenize.tokenize(io.BytesIO(content).readline)
    comments = [token.string.lower() for token in tokens if token.type == tokenize.COMMENT]
    if any("lizard" in comment and "forgive" in comment for comment in comments):
        raise ValueError(f"inline complexity suppression is forbidden: {path!r}")


def check_snapshot(base: str | None, ref: str) -> None:
    files = paths(base, ref)
    validate_paths(files)
    patterns = manifest(ref)
    selected = [path for path in files if path.endswith(".py")
                and not any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)]
    if not selected:
        print("CCN gate: no Python files to check")
        return
    check_analyzer()
    with tempfile.TemporaryDirectory(prefix="dbnt-ccn-") as directory:
        snapshots = []
        for index, path in enumerate(selected):
            content = blob(ref, path)
            reject_suppression(content, path)
            destination = Path(directory) / f"snapshot_{index}.py"
            print(f"Checking {path!r} as {destination.name}", flush=True)
            destination.write_bytes(content)
            snapshots.append(str(destination))
        result = subprocess.run([sys.executable, "-m", "lizard", *snapshots,
                                 "-C", "10", "-w", "-i", "0"], check=False)
        if result.returncode:
            raise ValueError("changed Python functions exceed CCN=10")
    print("CCN gate: changed Python functions are within CCN<=10")


def push_updates() -> None:
    updates = [line.split() for line in sys.stdin if line.strip()]
    if not updates:
        raise ValueError("pre-push requires Git ref updates on stdin")
    for update in updates:
        if len(update) != 4:
            raise ValueError("malformed pre-push ref update")
        _, local_sha, _, _ = update
        if local_sha == ZERO:
            continue
        merge_base = git("merge-base", "origin/main", local_sha).decode().strip()
        check_snapshot(merge_base, local_sha)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--staged", action="store_true")
    mode.add_argument("--push", action="store_true")
    mode.add_argument("--base")
    args = parser.parse_args()
    try:
        if args.staged:
            check_snapshot(None, ":")
        elif args.push:
            push_updates()
        else:
            base = git("merge-base", args.base, "HEAD").decode().strip()
            check_snapshot(base, "HEAD")
    except (OSError, ValueError, subprocess.CalledProcessError, tokenize.TokenError) as error:
        print(f"CCN gate ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
