#!/bin/bash
# Block edits to protected files.
# Used as a PreToolUse hook for Edit|Write tools.
# Exit 2 = block the action, stderr message goes to Claude as feedback.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
    exit 0
fi

PROTECTED_PATTERNS=(
    ".env"
    "uv.lock"
    ".pre-commit-config.yaml"
    ".git/"
    ".claude/settings.local.json"
    "data/raw/"
    "data/uploads/"
    "models/"
    "configs/production.yaml"
)

for pattern in "${PROTECTED_PATTERNS[@]}"; do
    if [[ "$FILE_PATH" == *"$pattern"* ]]; then
        echo "Blocked: '$FILE_PATH' matches protected pattern '$pattern'. Ask the user before modifying this file." >&2
        exit 2
    fi
done

exit 0
