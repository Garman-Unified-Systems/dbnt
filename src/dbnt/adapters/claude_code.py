"""Claude Code adapter — installs DBNT hooks into Claude Code."""

import json
from pathlib import Path
from typing import Any

from dbnt.adapters.base import BaseAdapter
from dbnt.core import Rule, RuleType


class ClaudeCodeAdapter(BaseAdapter):
    """Adapter for Claude Code.

    Installs two hooks:
    - UserPromptSubmit: DBNT protocol detection (DB/DBN/DBNM/DBYC commands)
    - Stop: Learning extraction from session transcript

    Supports both direct install (writes hooks to ~/.claude/hooks/) and
    plugin install (hooks registered via .claude-plugin/plugin.json).
    """

    def __init__(self, claude_dir: Path | None = None):
        self.claude_dir = claude_dir or Path.home() / ".claude"
        self.rules_dir = self.claude_dir / "rules"
        self.successes_dir = self.rules_dir / "successes"
        self.failures_dir = self.rules_dir / "failures"
        self.hooks_dir = self.claude_dir / "hooks"
        self.settings_path = self.claude_dir / "settings.json"

    def install(self) -> None:
        """Install DBNT into Claude Code."""
        if self.is_plugin_installed():
            print("DBNT plugin is already installed via Claude Code plugins.")
            print("Direct hook install is not needed — plugin handles registration.")
            print("To force direct install anyway, uninstall the plugin first.")
            return

        self.successes_dir.mkdir(parents=True, exist_ok=True)
        self.failures_dir.mkdir(parents=True, exist_ok=True)
        self.hooks_dir.mkdir(parents=True, exist_ok=True)

        self._install_protocol_hook()
        self._install_learning_hook()
        self._register_hooks()

        print(f"DBNT installed to Claude Code at {self.claude_dir}")
        print("  - Protocol detection hook (UserPromptSubmit)")
        print("  - Learning extraction hook (Stop)")

    def uninstall(self) -> None:
        """Remove DBNT from Claude Code."""
        for name in ("dbnt-protocol.sh", "dbnt-learn.sh"):
            hook = self.hooks_dir / name
            if hook.exists():
                hook.unlink()

        # Legacy cleanup
        legacy = self.hooks_dir / "dbnt-detector.sh"
        if legacy.exists():
            legacy.unlink()

        self._unregister_hooks()

        if self.is_plugin_installed():
            print("DBNT hooks uninstalled. Note: DBNT plugin is still installed.")
            print("To fully remove, also run: claude plugin uninstall dbnt")
        else:
            print("DBNT uninstalled from Claude Code")

    def is_plugin_installed(self) -> bool:
        """Check if DBNT is installed as a Claude Code plugin."""
        plugins_dir = self.claude_dir / "plugins"
        if not plugins_dir.exists():
            return False
        for plugin_dir in plugins_dir.iterdir():
            manifest = plugin_dir / ".claude-plugin" / "plugin.json"
            if manifest.exists():
                try:
                    data = json.loads(manifest.read_text())
                    if data.get("name") == "dbnt":
                        return True
                except (json.JSONDecodeError, OSError):
                    continue
        return False

    def get_rules_path(self) -> Path:
        return self.rules_dir

    def sync_rule(self, rule: Rule) -> None:
        if rule.type == RuleType.SUCCESS:
            path = self.successes_dir / f"{rule.id}.md"
        else:
            path = self.failures_dir / f"{rule.id}.md"
        path.write_text(rule.to_markdown())

    def is_installed(self) -> bool:
        return (self.hooks_dir / "dbnt-protocol.sh").exists()

    # ─── Hook Scripts ──────────────────────────────────────────────────

    def _install_protocol_hook(self) -> None:
        """Install the protocol detection hook (UserPromptSubmit).

        Detects DB/DBN/DBNM/DBYC commands and scores them.
        """
        hook = self.hooks_dir / "dbnt-protocol.sh"
        hook.write_text('''\
#!/usr/bin/env bash
# DBNT Protocol Detection Hook (UserPromptSubmit)
# Detects DB/DBN/DBNM/DBYC commands and tracks score

set -euo pipefail

INPUT=$(cat)
MESSAGE=$(echo "$INPUT" | jq -r '.user_prompt // .prompt // ""' 2>/dev/null || echo "")
[ -z "$MESSAGE" ] && echo '{"result":"continue"}' && exit 0

# Normalize
MSG_LOWER=$(echo "$MESSAGE" | tr '[:upper:]' '[:lower:]' | sed 's/^[[:space:]]*//')

# Protocol commands (must be at start of message)
POINTS=0
CMD=""
if echo "$MSG_LOWER" | /usr/bin/grep -qE "^dbyc(\\s|$|[.!])"; then
    CMD="DBYC"; POINTS=-2
elif echo "$MSG_LOWER" | /usr/bin/grep -qE "^dbnm(\\s|$|[.!])"; then
    CMD="DBNM"; POINTS=-1
elif echo "$MSG_LOWER" | /usr/bin/grep -qE "^dbn(\\s|$|[.!])"; then
    CMD="DBN"; POINTS=-1
elif echo "$MSG_LOWER" | /usr/bin/grep -qE "^db(\\s|$|[.!])"; then
    CMD="DB"; POINTS=-1
elif echo "$MSG_LOWER" | /usr/bin/grep -qE "^(fixed|ship it|nailed it)(\\s|$|[.!])"; then
    CMD="GOOD"; POINTS=3
elif echo "$MSG_LOWER" | /usr/bin/grep -qE "^tweak(\\s|$|[.!])"; then
    CMD="TWEAK"; POINTS=0
fi

[ -z "$CMD" ] && echo '{"result":"continue"}' && exit 0

# Log to score file
SCORE_DIR="$HOME/.dbnt"
mkdir -p "$SCORE_DIR"
SCORE_FILE="$SCORE_DIR/score.json"

if [ -f "$SCORE_FILE" ]; then
    TOTAL=$(jq -r '.total_points // 0' "$SCORE_FILE" 2>/dev/null || echo 0)
else
    TOTAL=0
fi

NEW_TOTAL=$(echo "$TOTAL + $POINTS" | bc)

# Append event
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EVENT="{\\"command\\":\\"$(echo $CMD | tr '[:upper:]' '[:lower:]')\\",\\"points\\":$POINTS,\\"timestamp\\":\\"$TIMESTAMP\\"}"

if [ -f "$SCORE_FILE" ]; then
    jq --argjson evt "$EVENT" '.total_points = '"$NEW_TOTAL"' | .events += [$evt] | .last_updated = "'"$TIMESTAMP"'"' "$SCORE_FILE" > "${SCORE_FILE}.tmp" && mv "${SCORE_FILE}.tmp" "$SCORE_FILE"
else
    echo "{\\"total_points\\":$NEW_TOTAL,\\"events\\":[$EVENT],\\"tweak_count\\":0,\\"last_updated\\":\\"$TIMESTAMP\\"}" | jq . > "$SCORE_FILE"
fi

echo '{"result":"continue"}'
exit 0
''')
        hook.chmod(0o755)

    def _install_learning_hook(self) -> None:
        """Install the learning extraction hook (Stop).

        Reads transcript, extracts learnings, stores in SQLite.
        Runs as a detached background process to not block session end.
        """
        hook = self.hooks_dir / "dbnt-learn.sh"
        hook.write_text('''\
#!/usr/bin/env bash
# DBNT Learning Extraction Hook (Stop)
# Extracts learnings from session transcript, stores in ~/.dbnt/learnings.db

set -euo pipefail

INPUT=$(cat)
TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path // ""' 2>/dev/null || echo "")
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // ""' 2>/dev/null || echo "")

[ -z "$TRANSCRIPT_PATH" ] || [ ! -f "$TRANSCRIPT_PATH" ] && echo '{"result":"continue"}' && exit 0

# Find python with dbnt installed
PYTHON=""
for p in python3 python; do
    if command -v "$p" >/dev/null 2>&1 && "$p" -c "import dbnt" 2>/dev/null; then
        PYTHON="$p"
        break
    fi
done

# Check common venv locations
if [ -z "$PYTHON" ]; then
    for venv in "$HOME/.dbnt/.venv/bin/python" "$HOME/.local/bin/python3"; do
        if [ -x "$venv" ] && "$venv" -c "import dbnt" 2>/dev/null; then
            PYTHON="$venv"
            break
        fi
    done
fi

[ -z "$PYTHON" ] && echo '{"result":"continue"}' && exit 0

# Run extraction in background (fire-and-forget)
nohup "$PYTHON" -c "
import sys
from pathlib import Path
from dbnt.extract import extract_from_transcript
from dbnt.learning import LearningStore

transcript = Path('$TRANSCRIPT_PATH').read_text()
learnings = extract_from_transcript(transcript)

if learnings:
    with LearningStore() as store:
        for l in learnings:
            store.add(
                text=l.text,
                source='session',
                domain=l.type.value,
                importance=l.importance,
                session_id='$SESSION_ID',
            )
" > /dev/null 2>&1 &
disown

echo '{"result":"continue"}'
exit 0
''')
        hook.chmod(0o755)

    # ─── Settings Registration ─────────────────────────────────────────

    def _register_hooks(self) -> None:
        """Register both hooks in settings.json."""
        if not self.settings_path.exists():
            settings: dict[str, Any] = {"hooks": {}}
        else:
            try:
                settings = json.loads(self.settings_path.read_text())
            except json.JSONDecodeError:
                settings = {"hooks": {}}

        if "hooks" not in settings:
            settings["hooks"] = {}

        hooks_dir = "$HOME/.claude/hooks"

        # Protocol hook → UserPromptSubmit
        self._ensure_hook_registered(
            settings, "UserPromptSubmit", f"{hooks_dir}/dbnt-protocol.sh"
        )

        # Learning hook → Stop
        self._ensure_hook_registered(
            settings, "Stop", f"{hooks_dir}/dbnt-learn.sh"
        )

        self.settings_path.write_text(json.dumps(settings, indent=2))

    def _ensure_hook_registered(
        self, settings: dict[str, Any], event: str, command: str
    ) -> None:
        """Ensure a hook command is registered for an event."""
        if event not in settings["hooks"]:
            settings["hooks"][event] = []

        for entry in settings["hooks"][event]:
            for hook in entry.get("hooks", []):
                if hook.get("command") == command:
                    return  # Already registered

        settings["hooks"][event].append(
            {"hooks": [{"type": "command", "command": command}]}
        )

    def _unregister_hooks(self) -> None:
        """Remove all DBNT hooks from settings.json."""
        if not self.settings_path.exists():
            return

        try:
            settings = json.loads(self.settings_path.read_text())
        except json.JSONDecodeError:
            return

        if "hooks" not in settings:
            return

        dbnt_cmds = {
            "$HOME/.claude/hooks/dbnt-protocol.sh",
            "$HOME/.claude/hooks/dbnt-learn.sh",
            "$HOME/.claude/hooks/dbnt-detector.sh",  # Legacy
        }

        for event in list(settings["hooks"]):
            settings["hooks"][event] = [
                entry
                for entry in settings["hooks"][event]
                if not any(
                    hook.get("command") in dbnt_cmds
                    for hook in entry.get("hooks", [])
                )
            ]

        self.settings_path.write_text(json.dumps(settings, indent=2))
