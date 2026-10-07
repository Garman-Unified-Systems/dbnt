"""Execute the complexity gate against staged and committed Git snapshots."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SIMPLE = 'def simple(value):\n    return value\n'
COMPLEX = 'def complex(value):\n' + ''.join(
    f'    if value == {number}:\n        return {number}\n' for number in range(11)
) + '    return -1\n'


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    git(tmp_path, 'init', '-b', 'main')
    git(tmp_path, 'config', 'user.name', 'Test Worker')
    git(tmp_path, 'config', 'user.email', 'test@example.invalid')
    shutil.copytree(REPO_ROOT / '.githooks', tmp_path / '.githooks')
    (tmp_path / 'scripts').mkdir()
    shutil.copy(REPO_ROOT / 'scripts/ccn_gate.py', tmp_path / 'scripts/ccn_gate.py')
    (tmp_path / 'baseline.py').write_text(SIMPLE)
    git(tmp_path, 'add', '.')
    git(tmp_path, 'commit', '-m', 'Initial fixture')
    git(tmp_path, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
    return tmp_path


def run(repo: Path, *args: str, stdin: str = '', env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, 'scripts/ccn_gate.py', *args], cwd=repo,
                          capture_output=True, text=True, input=stdin, env=env, check=False)


def stage(repo: Path, name: str, content: str) -> None:
    (repo / name).parent.mkdir(parents=True, exist_ok=True)
    (repo / name).write_text(content)
    git(repo, 'add', '--', name)


def commit(repo: Path) -> str:
    git(repo, 'commit', '-m', 'Fixture change')
    return git(repo, 'rev-parse', 'HEAD')


def test_real_analyzer_red_green_and_manifest(repo: Path) -> None:
    stage(repo, 'changed.py', COMPLEX)
    red = run(repo, '--staged')
    stage(repo, 'changed.py', SIMPLE)
    green = run(repo, '--staged')
    assert red.returncode == 1 and 'exceed CCN' in red.stderr
    assert green.returncode == 0
    stage(repo, 'changed.py', COMPLEX)
    stage(repo, 'scripts/ccn-allow-manifest.txt', '# Reviewed vendor pattern\nchanged.py\n')
    excluded = run(repo, '--staged')
    assert excluded.returncode == 0
    (repo / 'scripts/ccn-allow-manifest.txt').write_text('')
    assert run(repo, '--staged').returncode == 0


@pytest.mark.parametrize('hook', ['pre-commit', 'pre-merge-commit'])
def test_hooks_analyze_staged_contents(repo: Path, hook: str) -> None:
    stage(repo, 'changed.py', COMPLEX)
    (repo / 'changed.py').write_text(SIMPLE)
    env = dict(os.environ, PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ['PATH'])
    result = subprocess.run(['bash', f'.githooks/{hook}'], cwd=repo,
                            capture_output=True, text=True, env=env, check=False)
    assert result.returncode == 1
    stage(repo, 'changed.py', SIMPLE)
    (repo / 'changed.py').write_text(COMPLEX)
    result = subprocess.run(['bash', f'.githooks/{hook}'], cwd=repo,
                            capture_output=True, text=True, env=env, check=False)
    assert result.returncode == 0


@pytest.mark.parametrize('name', ['space name.py', 'newline\nname.py', '-option.py', 'wild[card]*.py'])
def test_paths_are_literal(repo: Path, name: str) -> None:
    stage(repo, name, COMPLEX)
    assert run(repo, '--staged').returncode == 1
    stage(repo, name, SIMPLE)
    assert run(repo, '--staged').returncode == 0


def test_renamed_files_are_analyzed(repo: Path) -> None:
    stage(repo, 'before.py', COMPLEX)
    commit(repo)
    git(repo, 'mv', 'before.py', 'after.py')
    assert run(repo, '--staged').returncode == 1


def test_deletions_do_not_analyze_missing_files(repo: Path) -> None:
    git(repo, 'rm', 'baseline.py')
    assert run(repo, '--staged').returncode == 0
    commit(repo)
    assert run(repo, '--base', 'origin/main').returncode == 0


@pytest.mark.parametrize('extension', ['go', 'rs', 'js', 'rb', 'cpp'])
def test_unsupported_language_fails(repo: Path, extension: str) -> None:
    stage(repo, f'file.{extension}', 'some code')
    result = run(repo, '--staged')
    assert result.returncode == 1 and 'unsupported imperative' in result.stderr


def test_push_analyzes_supplied_sha_not_head_or_worktree(repo: Path) -> None:
    stage(repo, 'changed.py', COMPLEX)
    rejected_sha = commit(repo)
    stage(repo, 'changed.py', SIMPLE)
    accepted_sha = commit(repo)
    update = f'refs/heads/topic {rejected_sha} refs/heads/topic {"0" * 40}\n'
    assert run(repo, '--push', stdin=update).returncode == 1
    (repo / 'changed.py').write_text(COMPLEX)
    update = f'refs/heads/topic {accepted_sha} refs/heads/topic {"0" * 40}\n'
    assert run(repo, '--push', stdin=update).returncode == 0


def test_push_checks_all_updates(repo: Path) -> None:
    stage(repo, 'changed.py', COMPLEX)
    complex_sha = commit(repo)
    stage(repo, 'changed.py', SIMPLE)
    simple_sha = commit(repo)
    updates = ''.join(f'refs/heads/{name} {sha} refs/heads/{name} {"0" * 40}\n'
                      for name, sha in [('simple', simple_sha), ('complex', complex_sha)])
    assert run(repo, '--push', stdin=updates).returncode == 1


def test_push_missing_base_and_missing_stdin_fail(repo: Path) -> None:
    sha = git(repo, 'rev-parse', 'HEAD')
    git(repo, 'update-ref', '-d', 'refs/remotes/origin/main')
    assert run(repo, '--push', stdin=f'refs/heads/topic {sha} refs/heads/topic {"0" * 40}\n').returncode == 1
    assert run(repo, '--push').returncode == 1
    assert run(repo, '--base', 'missing-base').returncode == 1


def test_deleting_remote_ref_needs_no_analysis(repo: Path) -> None:
    sha = git(repo, 'rev-parse', 'HEAD')
    assert run(repo, '--push', stdin=f'(delete) {"0" * 40} refs/heads/topic {sha}\n').returncode == 0


def test_unstaged_manifest_cannot_bypass_gate(repo: Path) -> None:
    stage(repo, 'changed.py', COMPLEX)
    (repo / 'scripts/ccn-allow-manifest.txt').write_text('changed.py\n')
    assert run(repo, '--staged').returncode == 1


def test_inline_suppression_fails(repo: Path) -> None:
    stage(repo, 'changed.py', '# lizard forgives\n' + COMPLEX)
    result = run(repo, '--staged')
    assert result.returncode == 1 and 'suppression' in result.stderr


def test_matching_version_module_spoof_cannot_bypass_gate(repo: Path) -> None:
    stage(repo, 'changed.py', COMPLEX)
    stage(repo, 'lizard.py', 'print("1.24.0")\n')
    env = dict(os.environ, PYTHONPATH=str(repo))
    red = run(repo, '--staged', env=env)
    assert red.returncode == 1 and 'exceed CCN' in red.stderr
    stage(repo, 'changed.py', SIMPLE)
    green = run(repo, '--staged', env=env)
    assert green.returncode == 0


def test_analyzer_version_remains_pinned(repo: Path) -> None:
    result = subprocess.run([sys.executable, '-I', '-m', 'lizard', '--version'],
                            cwd=repo, capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert result.stdout.strip() == '1.24.0'


def test_push_checks_entire_branch_against_main(repo: Path) -> None:
    stage(repo, "changed.py", COMPLEX)
    complex_sha = commit(repo)
    stage(repo, "unrelated.txt", "documentation")
    tip = commit(repo)
    update = f"refs/heads/topic {tip} refs/heads/topic {complex_sha}\n"
    assert run(repo, "--push", stdin=update).returncode == 1


def test_missing_analyzer_fails(repo: Path, tmp_path: Path) -> None:
    stage(repo, 'changed.py', SIMPLE)
    environment = tmp_path / 'without-analyzer'
    subprocess.run([sys.executable, '-m', 'venv', '--without-pip', str(environment)], check=True)
    interpreter = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    result = subprocess.run([str(interpreter), 'scripts/ccn_gate.py', '--staged'],
                            cwd=repo, capture_output=True, text=True, check=False)
    assert result.returncode == 1 and 'lizard==1.24.0 required' in result.stderr
