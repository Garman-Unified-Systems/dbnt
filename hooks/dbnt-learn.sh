#!/usr/bin/env bash
# DBNT Learning Extraction Hook (Stop)
# Extracts learnings from session transcript, stores in $DBNT_DIR/learnings.db

set -euo pipefail

DBNT_STATE_DIR="${DBNT_DIR:-$HOME/.dbnt}"
LOG="$DBNT_STATE_DIR/learn-hook.log"
mkdir -p "$DBNT_STATE_DIR"

INPUT=$(cat)
TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path // ""' 2>/dev/null || echo "")
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // ""' 2>/dev/null || echo "")

# No transcript or file missing → skip
if [ -z "$TRANSCRIPT_PATH" ] || [ ! -f "$TRANSCRIPT_PATH" ]; then
    echo '{"continue":true}'
    exit 0
fi

# Find python with dbnt installed
PYTHON=""
for p in python3 python; do
    if command -v "$p" >/dev/null 2>&1 && "$p" -c "import dbnt" 2>/dev/null; then
        PYTHON="$p"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    for venv in "$DBNT_STATE_DIR/.venv/bin/python" "$HOME/.local/bin/python3"; do
        if [ -x "$venv" ] && "$venv" -c "import dbnt" 2>/dev/null; then
            PYTHON="$venv"
            break
        fi
    done
fi

[ -z "$PYTHON" ] && echo '{"continue":true}' && exit 0

# Fire-and-forget: spawn extraction detached so the hook returns fast
nohup "$PYTHON" -c "
import sys, logging
from pathlib import Path

logging.basicConfig(
    filename='$LOG',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
)
log = logging.getLogger('dbnt-learn')

try:
    from dbnt.extract import extract_from_transcript
    from dbnt.learning import LearningStore

    transcript_path = Path('$TRANSCRIPT_PATH')
    session_id = '$SESSION_ID'

    raw = transcript_path.read_text()
    log.info(f'Transcript: {transcript_path.name} ({len(raw)} bytes)')

    learnings = extract_from_transcript(raw)
    log.info(f'Extracted {len(learnings)} learning(s)')

    if learnings:
        with LearningStore() as store:
            for l in learnings:
                lid = store.add(
                    text=l.text,
                    source='session',
                    domain=l.type.value,
                    importance=l.importance,
                    session_id=session_id,
                )
                log.info(f'  Stored #{lid}: [{l.type.value}] {l.text[:80]}')
    else:
        log.info('No learnings extracted')

except Exception as e:
    log.error(f'Extraction failed: {e}', exc_info=True)
" >> "$LOG" 2>&1 &
disown

echo '{"continue":true}'
exit 0
