"""Tests for runner seat rule slices."""

import pytest
from click.testing import CliRunner

from dbnt.cli import main
from dbnt.core import RuleType
from dbnt.seats import (
    SeatError,
    capture_seat_rule,
    decay_key,
    list_seat_names,
    load_seat_rules,
    render_prompt_block,
    seat_rules_dir,
    validate_seat,
)


@pytest.fixture
def state_root(monkeypatch, tmp_path):
    root = tmp_path / "dbnt"
    monkeypatch.setenv("DBNT_DIR", str(root))
    return root


class TestSeatResolution:
    """Test seat path resolution and validation."""

    def test_resolves_slice_under_state_root(self, state_root):
        assert seat_rules_dir("codex@dru") == state_root / "rules" / "seats" / "codex@dru"

    def test_explicit_root_overrides_environment(self, state_root, tmp_path):
        explicit = tmp_path / "explicit"
        assert seat_rules_dir("codex@dru", explicit) == explicit / "rules" / "seats" / "codex@dru"

    @pytest.mark.parametrize(
        "seat",
        [
            "",
            "   ",
            "../etc",
            "codex@dru/../../etc",
            "codex@dru/extra",
            "codex\\dru",
            "Codex@Dru",
            "codex",
            "codex@",
            "@dru",
            "a@b@c",
            "codex@dru ",
        ],
    )
    def test_rejects_invalid_seat(self, seat):
        with pytest.raises(SeatError):
            validate_seat(seat)

    def test_rejects_overlong_seat(self):
        with pytest.raises(SeatError, match="at most"):
            validate_seat(f"{'a' * 200}@dru")

    def test_accepts_dotted_seat(self):
        assert validate_seat("codex.gpt@dru-01.local") == "codex.gpt@dru-01.local"


class TestSeatCapture:
    """Test capture and read-back for both directions."""

    def test_capture_failure_round_trips(self, state_root):
        capture = capture_seat_rule(
            "codex@dru",
            "Guessed a file hash",
            RuleType.FAILURE,
            "protocol",
            "Two rows failed on unverified digests",
        )

        rules = load_seat_rules("codex@dru")

        assert capture.path.parent == state_root / "rules" / "seats" / "codex@dru" / "failures"
        assert len(rules) == 1
        assert rules[0].type is RuleType.FAILURE
        assert rules[0].category.value == "protocol"
        assert rules[0].pattern == "Guessed a file hash"
        assert rules[0].context == "Two rows failed on unverified digests"
        assert rules[0].weight == 1.0

    def test_capture_success_round_trips(self, state_root):
        capture = capture_seat_rule(
            "codex@dru",
            "Re-read the artifact after every write",
            RuleType.SUCCESS,
            "code",
            "Caught a dropped mention",
        )

        rules = load_seat_rules("codex@dru")

        assert capture.path.parent == state_root / "rules" / "seats" / "codex@dru" / "successes"
        assert len(rules) == 1
        assert rules[0].type is RuleType.SUCCESS
        assert rules[0].category.value == "code"
        assert rules[0].weight == 1.5

    def test_capture_uses_existing_markdown_shape(self, state_root):
        capture = capture_seat_rule(
            "codex@dru", "Guessed a file hash", RuleType.FAILURE, "protocol", "Reason here"
        )
        body = capture.path.read_text()

        assert body.startswith("# Failure: Guessed a file hash")
        assert "**Category**: protocol" in body
        assert "## Context\n\nReason here" in body
        assert "## Pattern\n\nGuessed a file hash" in body

    def test_capture_leaves_global_rules_untouched(self, state_root):
        capture_seat_rule("codex@dru", "Guessed a file hash", RuleType.FAILURE, "protocol")

        global_files = list((state_root / "rules").glob("successes/*.md"))
        global_files += list((state_root / "rules").glob("failures/*.md"))
        assert global_files == []

    def test_same_pattern_twice_refuses_without_replace(self, state_root):
        first = capture_seat_rule("codex@dru", "Guessed a file hash", RuleType.FAILURE, "protocol")

        with pytest.raises(SeatError, match="already exists"):
            capture_seat_rule("codex@dru", "Guessed a file hash", RuleType.FAILURE, "protocol")

        assert len(list(first.path.parent.glob("*.md"))) == 1

    def test_same_pattern_with_replace_updates_in_place(self, state_root):
        first = capture_seat_rule(
            "codex@dru", "Guessed a file hash", RuleType.FAILURE, "protocol", "First reason"
        )
        second = capture_seat_rule(
            "codex@dru",
            "Guessed a file hash",
            RuleType.FAILURE,
            "protocol",
            "Second reason",
            replace_existing=True,
        )

        assert second.replaced is True
        assert second.path == first.path
        assert second.rule.context == "Second reason"
        assert len(list(first.path.parent.glob("*.md"))) == 1

    def test_pattern_match_ignores_case_and_whitespace(self, state_root):
        capture_seat_rule("codex@dru", "Guessed a file hash", RuleType.FAILURE, "protocol")

        with pytest.raises(SeatError, match="already exists"):
            capture_seat_rule("codex@dru", "  guessed a  FILE hash ", RuleType.FAILURE, "protocol")

    def test_distinct_patterns_coexist(self, state_root):
        capture_seat_rule("codex@dru", "Guessed a file hash", RuleType.FAILURE, "protocol")
        capture_seat_rule("codex@dru", "Skipped the read-back", RuleType.FAILURE, "protocol")

        assert len(load_seat_rules("codex@dru")) == 2

    def test_categories_are_direction_scoped(self, state_root):
        with pytest.raises(SeatError, match="not valid for success"):
            capture_seat_rule("codex@dru", "Guessed a file hash", RuleType.SUCCESS, "protocol")

    def test_empty_pattern_is_rejected(self, state_root):
        with pytest.raises(SeatError, match="pattern must not be empty"):
            capture_seat_rule("codex@dru", "   ", RuleType.FAILURE, "protocol")


class TestSeatRead:
    """Test listing and prompt rendering."""

    def test_missing_slice_reads_empty(self, state_root):
        assert load_seat_rules("codex@dru") == []

    def test_lists_captured_seats(self, state_root):
        capture_seat_rule("codex@dru", "Guessed a file hash", RuleType.FAILURE, "protocol")
        capture_seat_rule("melvil@gus", "Wrote before reading", RuleType.FAILURE, "protocol")

        assert list_seat_names() == ["codex@dru", "melvil@gus"]

    def test_prompt_block_is_only_rules(self, state_root):
        capture_seat_rule("codex@dru", "Guessed a file hash", RuleType.FAILURE, "protocol")
        capture_seat_rule("codex@dru", "Re-read after write", RuleType.SUCCESS, "code")

        block = render_prompt_block("codex@dru", load_seat_rules("codex@dru"))

        assert block.splitlines() == [
            "## Seat rules: codex@dru",
            "",
            "- [success/code] Re-read after write",
            "- [failure/protocol] Guessed a file hash",
        ]

    def test_prompt_block_for_empty_seat(self, state_root):
        block = render_prompt_block("codex@dru", [])
        assert block == "## Seat rules: codex@dru\n\n_No seat rules captured yet._"

    def test_decay_key_is_namespaced_by_seat(self):
        assert decay_key("codex@dru", "protocol-abc") == "codex@dru/protocol-abc"


class TestSeatCli:
    """Test the seat commands through the CLI."""

    def test_seat_capture_then_seat_rules(self, state_root):
        runner = CliRunner()
        captured = runner.invoke(
            main,
            [
                "seat-capture",
                "codex@dru",
                "Guessed a file hash",
                "-c",
                "protocol",
                "-x",
                "Read the file first",
            ],
        )
        listed = runner.invoke(main, ["seat-rules", "codex@dru"])

        assert captured.exit_code == 0
        assert "Seat rule protocol-guessed-a-file-hash" in captured.output
        assert listed.exit_code == 0
        assert "SEAT codex@dru (1):" in listed.output
        assert "[protocol  ]" in listed.output
        assert "(stable)" in listed.output

    def test_seat_capture_success_direction(self, state_root):
        result = CliRunner().invoke(
            main,
            ["seat-capture", "codex@dru", "Re-read after write", "-k", "success", "-c", "code"],
        )

        assert result.exit_code == 0
        assert load_seat_rules("codex@dru")[0].type is RuleType.SUCCESS

    def test_seat_rules_prompt_prints_block_only(self, state_root):
        runner = CliRunner()
        runner.invoke(main, ["seat-capture", "codex@dru", "Guessed a file hash", "-c", "protocol"])

        result = runner.invoke(main, ["seat-rules", "codex@dru", "--prompt"])

        assert result.exit_code == 0
        assert result.output == (
            "## Seat rules: codex@dru\n\n- [failure/protocol] Guessed a file hash\n"
        )

    def test_seat_rules_all_lists_every_seat(self, state_root):
        runner = CliRunner()
        runner.invoke(main, ["seat-capture", "codex@dru", "Guessed a hash", "-c", "protocol"])
        runner.invoke(main, ["seat-capture", "melvil@gus", "Skipped a read", "-c", "protocol"])

        result = runner.invoke(main, ["seat-rules", "--all"])

        assert result.exit_code == 0
        assert "SEAT codex@dru (1):" in result.output
        assert "SEAT melvil@gus (1):" in result.output

    def test_seat_rules_all_without_slices(self, state_root):
        result = CliRunner().invoke(main, ["seat-rules", "--all"])

        assert result.exit_code == 0
        assert "No seat slices found." in result.output

    def test_seat_rules_rejects_traversal(self, state_root):
        result = CliRunner().invoke(main, ["seat-rules", "../etc"])

        assert result.exit_code != 0
        assert "path traversal" in result.output

    def test_seat_rules_requires_a_seat(self, state_root):
        result = CliRunner().invoke(main, ["seat-rules"])

        assert result.exit_code != 0
        assert "Missing argument 'SEAT'" in result.output

    def test_seat_capture_duplicate_reports_error(self, state_root):
        runner = CliRunner()
        runner.invoke(main, ["seat-capture", "codex@dru", "Guessed a hash", "-c", "protocol"])

        result = runner.invoke(
            main, ["seat-capture", "codex@dru", "Guessed a hash", "-c", "protocol"]
        )

        assert result.exit_code != 0
        assert "--replace" in result.output

    def test_seat_capture_replace_flag(self, state_root):
        runner = CliRunner()
        runner.invoke(main, ["seat-capture", "codex@dru", "Guessed a hash", "-c", "protocol"])

        result = runner.invoke(
            main,
            ["seat-capture", "codex@dru", "Guessed a hash", "-c", "protocol", "--replace"],
        )

        assert result.exit_code == 0
        assert result.output.startswith("~")
        assert len(load_seat_rules("codex@dru")) == 1

    def test_seat_capture_rejects_mismatched_category(self, state_root):
        result = CliRunner().invoke(
            main,
            ["seat-capture", "codex@dru", "Guessed a hash", "-k", "success", "-c", "protocol"],
        )

        assert result.exit_code != 0
        assert "not valid for success" in result.output


class TestSeatRecurrenceWiring:
    """Test that seats reach the recurrence and decay reporting paths."""

    def test_sweep_reports_seat_rules(self, state_root):
        runner = CliRunner()
        runner.invoke(main, ["seat-capture", "codex@dru", "Guessed a hash", "-c", "protocol"])

        result = runner.invoke(main, ["sweep"])

        assert result.exit_code == 0
        assert "Seat rules:" in result.output
        assert "codex@dru  protocol-guessed-a-hash" in result.output

    def test_sweep_output_unchanged_without_seats(self, state_root):
        runner = CliRunner()
        runner.invoke(main, ["success", "Use bun not npm", "-c", "code"])

        result = runner.invoke(main, ["sweep"])

        assert result.exit_code == 0
        assert "Seat rules:" not in result.output
        assert result.output == "Rules: 1 total\n  Healthy: 1\n  Review:  0\n  Archive: 0\n"

    def test_promote_without_seat_keeps_global_behaviour(self, state_root):
        runner = CliRunner()
        for _ in range(3):
            runner.invoke(main, ["learn", "Guessed a file hash again", "-d", "code"])

        result = runner.invoke(main, ["promote"])

        assert result.exit_code == 0
        assert "pattern(s) promoted" in result.output
        assert load_seat_rules("codex@dru") == []

    def test_promote_with_seat_writes_into_slice(self, state_root):
        runner = CliRunner()
        for _ in range(3):
            runner.invoke(main, ["learn", "Guessed a file hash again", "-d", "code"])

        result = runner.invoke(main, ["promote", "--seat", "codex@dru"])

        assert result.exit_code == 0
        assert len(load_seat_rules("codex@dru")) == 1


class TestSeatStateRoot:
    """Test that the seat slice honours the shared state root contract."""

    def test_state_directory_is_honoured(self, state_root):
        capture = capture_seat_rule("codex@dru", "Guessed a hash", RuleType.FAILURE, "protocol")

        assert capture.path.parent == (state_root / "rules" / "seats" / "codex@dru" / "failures")
        assert capture.path.name.startswith("protocol-guessed-a-hash-")
        assert capture.path.is_file()

    def test_seats_survive_a_root_switch(self, monkeypatch, tmp_path):
        first = tmp_path / "first"
        second = tmp_path / "second"

        monkeypatch.setenv("DBNT_DIR", str(first))
        capture_seat_rule("codex@dru", "Guessed a hash", RuleType.FAILURE, "protocol")
        assert len(load_seat_rules("codex@dru")) == 1

        monkeypatch.setenv("DBNT_DIR", str(second))
        assert load_seat_rules("codex@dru") == []
