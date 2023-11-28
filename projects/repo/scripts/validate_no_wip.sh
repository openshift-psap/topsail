#! /usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace

# This script ensures that none of the commits have the WIP flag in their message title

WIP_MARKER="WIP"

first_parent=$(git log --pretty=%P -n 1 | cut -d" " -f1)
second_parent=$(git log --pretty=%P -n 1 | cut -d" " -f2)

commits=$(git log --pretty=format:'%h - %s' --abbrev-commit "${first_parent}..${second_parent}")

if [[ -z "${GITHUB_REF:-}" ]]; then
    echo "ERROR: GITHUB_REF, cannot run outside of a github action."
    exit 1
fi

which jq >/dev/null # fails if jq isn't in the path

PR_NUMBER=$(echo "$GITHUB_REF" | awk 'BEGIN { FS = "/" } ; { print $3 }')
PR_URL="https://api.github.com/repos/$GITHUB_REPOSITORY/pulls/$PR_NUMBER"

echo "Fetching the PR from '$PR_URL' ..."
pr_title=$(curl -sSf "$PR_URL" | jq -r .title)

echo "PR title: $pr_title"
echo "PR commits:"
echo "$commits"

if echo "$pr_title" | grep "$WIP_MARKER" --quiet; then
    echo "ERROR: found the '$WIP_MARKER' marker in the PR title..."
    exit 1
fi

if echo "$commits" | grep "$WIP_MARKER" --quiet; then
    echo "ERROR: found the '$WIP_MARKER' marker in the PR commits..."
    exit 1
fi
