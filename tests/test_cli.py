"""Regression tests for the public DBNT command-line interface."""

import pytest
from click.testing import CliRunner

from dbnt.cli import main


def test_detect_perfect_reports_positive_strong_signal():
    result = CliRunner().invoke(main, ["detect", "perfect"])

    assert result.exit_code == 0
    assert "Type: positive" in result.output
    assert "Strength: strong" in result.output


def test_detect_ok_reports_neutral_signal():
    result = CliRunner().invoke(main, ["detect", "ok"])

    assert result.exit_code == 0
    assert "Type: neutral" in result.output


def test_process_dbn_reports_command_path(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    result = CliRunner().invoke(main, ["process", "dbn"])

    assert result.exit_code == 0
    assert "Command: DBN" in result.output
    assert "Action: encode_success" in result.output


def test_process_ordinary_text_falls_back_to_signal_detection(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    result = CliRunner().invoke(main, ["process", "ordinary status update"])

    assert result.exit_code == 0
    assert "Signal: neutral (weak)" in result.output
    assert "Weight: 0.0" in result.output


@pytest.mark.parametrize(
    ("command", "valid_categories"),
    [
        ("success", ("format", "code", "explain", "tool", "comm")),
        ("failure", ("protocol", "preference", "waste", "gap", "integration")),
    ],
)
def test_rule_commands_reject_invalid_category(command, valid_categories):
    result = CliRunner().invoke(
        main,
        [command, "test pattern", "--category", "not-a-category"],
    )

    assert result.exit_code != 0
    assert "Invalid value for '--category' / '-c'" in result.output
    assert all(f"'{category}'" in result.output for category in valid_categories)
