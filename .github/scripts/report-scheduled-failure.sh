#!/usr/bin/env bash
set -euo pipefail

LABEL="scheduled-failure"
TITLE="Scheduled dependency check failed"

# Ensure the label exists. --force makes this idempotent: creates if absent,
# updates color/description without error if present.
gh label create "$LABEL" \
  --color "FBCA04" \
  --description "Weekly dependency check failures" \
  --force

# Find an open issue with our label, if any. --jq '.[0].number // empty'
# yields the first number or an empty string when there are no matches.
existing=$(gh issue list --label "$LABEL" --state open --json number --jq '.[0].number // empty')

if [ -z "$existing" ]; then
  body=$(printf '%s\n\n%s\n\n%s\n\n%s' \
    "The weekly scheduled dependency check failed." \
    "First failing run: ${RUN_URL}" \
    "Likely cause: a transitive dev or lint dependency (ruff, mypy, pyrefly, pytest, faststream, typing-extensions) released a breaking change. Reproduce locally with \`just install\` then \`just lint\` and \`just test\`." \
    "Close this issue once fixed. The next scheduled failure will open a fresh issue.")
  gh issue create --title "$TITLE" --label "$LABEL" --body "$body"
else
  gh issue comment "$existing" --body "Failed again: ${RUN_URL}"
fi
