#!/bin/bash
# Auto-format Python files after edits.
# Used as a PostToolUse hook for Edit|Write tools.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Only format Python files
if [[ "$FILE_PATH" == *.py ]]; then
    uv run ruff format "$FILE_PATH" 2>/dev/null
    uv run ruff check "$FILE_PATH" --fix --quiet 2>/dev/null
fi

exit 0
