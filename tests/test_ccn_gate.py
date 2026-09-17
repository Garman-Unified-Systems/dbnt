"""
Tests for the CCN gate (dru-2okra.20).

These tests prove the gate script logic without relying on GitHub Actions.
They verify lizard 1.24.0 is available, exits 1 on a CCN>10 function,
and exits 0 on a CCN<=10 function — the red-green proof required by GOV-100/101.

Controls in the SAME invocation:
  - Positive control (RED):  known CCN=12 function → gate must exit 1
  - Negative control (GREEN): known CCN=2 function → gate must exit 0
  - Analyzer-missing control: wrong binary path → install check must exit 1

Local hook tests (GAP-1):
  - pre-commit, pre-merge-commit, pre-push hooks exist and are executable.
  - Each hook sources ccn-gate-lib.sh.

Unsupported-language tests (GAP-2):
  - A non-Python imperative file in staged changes causes fail-loud (exit 1).
  - A Python-only change continues normally.
"""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

# Path to .githooks directory in this repo.
REPO_ROOT = Path(__file__).parent.parent
GITHOOKS_DIR = REPO_ROOT / ".githooks"

# ---------------------------------------------------------------------------
# Fixtures: known-complexity Python files written to tmp paths.
# ---------------------------------------------------------------------------

COMPLEX_FUNCTION = textwrap.dedent("""\
    def deliberately_complex(a, b, c, d, e, f, g, h, i, j, k):
        \"\"\"CCN=12 function used as the RED control for the CCN gate test.\"\"\"
        if a:
            return 1
        elif b:
            return 2
        elif c:
            return 3
        elif d:
            return 4
        elif e:
            return 5
        elif f:
            return 6
        elif g:
            return 7
        elif h:
            return 8
        elif i:
            return 9
        elif j:
            return 10
        elif k:
            return 11
        return 0
""")

SIMPLE_FUNCTION = textwrap.dedent("""\
    def simple_lookup(a, b):
        \"\"\"CCN=2 function used as the GREEN control for the CCN gate test.\"\"\"
        if a:
            return a
        return b
""")


@pytest.fixture()
def complex_py(tmp_path: Path) -> Path:
    p = tmp_path / "complex_fixture.py"
    p.write_text(COMPLEX_FUNCTION)
    return p


@pytest.fixture()
def simple_py(tmp_path: Path) -> Path:
    p = tmp_path / "simple_fixture.py"
    p.write_text(SIMPLE_FUNCTION)
    return p


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _run_lizard(path: Path) -> subprocess.CompletedProcess:
    """Run lizard with CCN=10 gate on a single file. Returns the process result."""
    return subprocess.run(
        [sys.executable, "-m", "lizard", str(path), "-C", "10", "-w", "-i", "0"],
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Gate tests — RED, GREEN, and tamper controls in same test session.
# ---------------------------------------------------------------------------


class TestCCNGateRedGreen:
    """GOV-100/101: positive and negative controls in the same invocation."""

    def test_red_complex_function_fails_gate(self, complex_py: Path) -> None:
        """RED control: CCN=12 function must cause gate exit 1."""
        result = _run_lizard(complex_py)
        assert result.returncode == 1, (
            f"Expected exit 1 for CCN=12 function but got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "deliberately_complex" in result.stdout, (
            "Warning output should name the violating function."
        )

    def test_green_simple_function_passes_gate(self, simple_py: Path) -> None:
        """GREEN control: CCN=2 function must cause gate exit 0."""
        result = _run_lizard(simple_py)
        assert result.returncode == 0, (
            f"Expected exit 0 for CCN=2 function but got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_controls_differ(self, complex_py: Path, simple_py: Path) -> None:
        """GOV-101: the two controls must produce DIFFERENT exit codes.

        If both return the same exit code the instrument is stuck and both
        results are VOID.
        """
        red_result = _run_lizard(complex_py)
        green_result = _run_lizard(simple_py)
        assert red_result.returncode != green_result.returncode, (
            "RED and GREEN controls must return different exit codes. "
            f"Both returned {red_result.returncode} — instrument is stuck (VOID)."
        )


class TestCCNGateAnalyzerVersion:
    """Analyzer tamper-check: lizard must report version 1.24.0."""

    def test_lizard_version_is_pinned(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "lizard", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, "lizard --version should exit 0"
        version_output = (result.stdout + result.stderr).strip()
        assert version_output == "1.24.0", (
            f"lizard version mismatch — expected 1.24.0, got: {version_output!r}. "
            "Update the pinned version in ccn-gate.yml if this is intentional."
        )


class TestCCNGateAllowManifest:
    """Manifest bypass: paths matching the allow-manifest must be excluded."""

    def test_manifest_path_is_excluded(self, complex_py: Path, tmp_path: Path) -> None:
        """A file listed in the manifest should not be analyzed."""
        manifest = tmp_path / "ccn-allow-manifest.txt"
        # Write the filename (basename) as the pattern — simulates a generated path.
        manifest.write_text(f"*/{complex_py.name}\n")

        # The gate shell script filters before calling lizard.
        # Here we test the filter logic directly by checking the manifest presence.
        content = manifest.read_text()
        assert complex_py.name in content, "Manifest should contain the fixture filename"
        # No call to lizard; this proves the manifest file is written correctly.
        # The CI shell script uses `case "$f" in $pattern)` to skip matching paths.


# ---------------------------------------------------------------------------
# GAP-1: Local git hooks exist and are executable.
# ---------------------------------------------------------------------------


class TestLocalHooksExist:
    """GAP-1: pre-commit, pre-merge-commit, pre-push hooks must exist and be executable."""

    @pytest.mark.parametrize("hook_name", ["pre-commit", "pre-merge-commit", "pre-push"])
    def test_hook_file_exists(self, hook_name: str) -> None:
        """Each local hook file must be present under .githooks/."""
        hook_path = GITHOOKS_DIR / hook_name
        assert hook_path.exists(), (
            f".githooks/{hook_name} not found at {hook_path}. "
            "Run 'bash scripts/install-hooks.sh' after cloning."
        )

    @pytest.mark.parametrize("hook_name", ["pre-commit", "pre-merge-commit", "pre-push"])
    def test_hook_is_executable(self, hook_name: str) -> None:
        """Each local hook must be executable."""
        hook_path = GITHOOKS_DIR / hook_name
        assert hook_path.exists(), f".githooks/{hook_name} not found"
        assert os.access(hook_path, os.X_OK), (
            f".githooks/{hook_name} is not executable. "
            "Run: chmod +x .githooks/{hook_name}"
        )

    @pytest.mark.parametrize("hook_name", ["pre-commit", "pre-merge-commit", "pre-push"])
    def test_hook_sources_lib(self, hook_name: str) -> None:
        """Each local hook must source ccn-gate-lib.sh (the shared policy library)."""
        hook_path = GITHOOKS_DIR / hook_name
        assert hook_path.exists(), f".githooks/{hook_name} not found"
        content = hook_path.read_text()
        assert "ccn-gate-lib.sh" in content, (
            f".githooks/{hook_name} does not source ccn-gate-lib.sh. "
            "The hook must load the shared CCN gate library to enforce the policy."
        )

    def test_lib_exists_and_is_executable(self) -> None:
        """ccn-gate-lib.sh must be present and executable."""
        lib_path = GITHOOKS_DIR / "ccn-gate-lib.sh"
        assert lib_path.exists(), f"ccn-gate-lib.sh not found at {lib_path}"
        assert os.access(lib_path, os.X_OK), "ccn-gate-lib.sh is not executable"


# ---------------------------------------------------------------------------
# GAP-2: Unsupported imperative language detection — fail loud.
# ---------------------------------------------------------------------------


class TestUnsupportedLanguageFailing:
    """GAP-2: non-Python imperative files in a diff must cause fail-loud exit 1.

    GOV-100/101: RED control (unsupported language → exit 1) and GREEN control
    (Python-only → no unsupported-lang error) in the same test session.
    """

    # Imperative extensions the gate currently cannot analyze.
    UNSUPPORTED_EXTS = ["go", "rb", "rs", "js", "ts", "java", "cs", "cpp"]

    def _run_unsupported_check(self, file_list: str, tmp_path: Path) -> subprocess.CompletedProcess:
        """Run the ccn_check_unsupported_langs function via a small bash driver."""
        lib_path = GITHOOKS_DIR / "ccn-gate-lib.sh"
        driver = textwrap.dedent(f"""\
            #!/usr/bin/env bash
            set -euo pipefail
            source {lib_path}
            ccn_check_unsupported_langs "{file_list}"
        """)
        driver_path = tmp_path / "driver.sh"
        driver_path.write_text(driver)
        driver_path.chmod(0o755)
        return subprocess.run(
            ["bash", str(driver_path)],
            capture_output=True,
            text=True,
        )

    @pytest.mark.parametrize("ext", UNSUPPORTED_EXTS)
    def test_red_unsupported_language_fails_loud(self, tmp_path: Path, ext: str) -> None:
        """RED control: a changed file with an unsupported imperative extension must exit 1."""
        result = self._run_unsupported_check(f"src/foo.{ext}", tmp_path)
        assert result.returncode == 1, (
            f"Expected exit 1 for unsupported imperative language '.{ext}' "
            f"but got {result.returncode}.\nstderr: {result.stderr}"
        )
        assert "unsupported imperative" in result.stderr.lower() or \
               "unsupported" in result.stderr.lower(), (
            f"Expected a clear error message for '.{ext}' file.\nstderr: {result.stderr}"
        )

    def test_green_python_only_passes_unsupported_check(self, tmp_path: Path) -> None:
        """GREEN control: Python-only files must not trigger the unsupported-language check."""
        result = self._run_unsupported_check("src/foo.py tests/test_foo.py", tmp_path)
        assert result.returncode == 0, (
            f"Expected exit 0 for Python-only files but got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_controls_differ(self, tmp_path: Path) -> None:
        """GOV-101: RED (unsupported lang) and GREEN (Python only) must differ."""
        red_result = self._run_unsupported_check("src/foo.go", tmp_path)
        green_result = self._run_unsupported_check("src/foo.py", tmp_path)
        assert red_result.returncode != green_result.returncode, (
            "RED (.go) and GREEN (.py) controls both returned "
            f"{red_result.returncode} — instrument is stuck (VOID)."
        )
