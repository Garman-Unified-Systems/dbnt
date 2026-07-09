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
if echo "$MSG_LOWER" | /usr/bin/grep -qE "^dbyc(\s|$|[.!])"; then
    CMD="DBYC"; POINTS=-2
elif echo "$MSG_LOWER" | /usr/bin/grep -qE "^dbnm(\s|$|[.!])"; then
    CMD="DBNM"; POINTS=-1
elif echo "$MSG_LOWER" | /usr/bin/grep -qE "^dbn(\s|$|[.!])"; then
    CMD="DBN"; POINTS=-1
elif echo "$MSG_LOWER" | /usr/bin/grep -qE "^db(\s|$|[.!])"; then
    CMD="DB"; POINTS=-1
elif echo "$MSG_LOWER" | /usr/bin/grep -qE "^(fixed|ship it|nailed it)(\s|$|[.!])"; then
    CMD="GOOD"; POINTS=3
elif echo "$MSG_LOWER" | /usr/bin/grep -qE "^tweak(\s|$|[.!])"; then
    CMD="TWEAK"; POINTS=0
fi

[ -z "$CMD" ] && echo '{"result":"continue"}' && exit 0

# Log to score file
SCORE_DIR="$HOME/.dbnt"
mkdir -p "$SCORE_DIR"
SCORE_FILE="$SCORE_DIR/score.json"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

initialize_score_file() {
    echo '{"total_points":0,"events":[],"tweak_count":0,"last_updated":"'"$TIMESTAMP"'"}' | jq . > "$SCORE_FILE"
}

validate_score_file() {
    jq -e '
        type == "object"
        and ((.total_points // 0) | type == "number")
        and ((.tweak_count // 0) | type == "number")
        and ((.tweak_count // 0) >= 0)
        and (((.tweak_count // 0) | floor) == (.tweak_count // 0))
        and ((.events // []) | type == "array")
        and ((.events // []) | all(.[]; type == "object"
            and ((has("points") | not) or (.points | type == "number"))
            and ((has("delta") | not) or (.delta | type == "number"))
            and ((has("score") | not) or (.score | type == "number"))
            and ((has("weight") | not) or (.weight | type == "number"))))
    ' "$1" >/dev/null 2>&1
}

if [ -f "$SCORE_FILE" ] && ! validate_score_file "$SCORE_FILE"; then
    mv "$SCORE_FILE" "${SCORE_FILE}.corrupt.$(date -u +"%Y%m%dT%H%M%SZ").$$"
fi

if [ ! -f "$SCORE_FILE" ]; then
    initialize_score_file
fi

TOTAL=$(jq -r '.total_points // 0' "$SCORE_FILE" 2>/dev/null || echo 0)

NEW_TOTAL=$(echo "$TOTAL + $POINTS" | bc)

# Append event
EVENT="{\"command\":\"$(echo $CMD | tr '[:upper:]' '[:lower:]')\",\"points\":$POINTS,\"timestamp\":\"$TIMESTAMP\"}"
TMP_SCORE="${SCORE_FILE}.$$.tmp"
if ! jq --argjson evt "$EVENT" '.total_points = '"$NEW_TOTAL"' | .events += [$evt] | .last_updated = "'"$TIMESTAMP"'"' "$SCORE_FILE" > "$TMP_SCORE"; then
    rm -f "$TMP_SCORE"
    echo '{"result":"continue"}'
    exit 0
fi
mv "$TMP_SCORE" "$SCORE_FILE"

echo '{"result":"continue"}'
exit 0
