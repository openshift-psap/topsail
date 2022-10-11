#! /usr/bin/env bash

# This script ensures that none of the commits have the WIP flag in their message title

WIP_MARKER="WIP"

first_parent=$(git log --pretty=%P -n 1 | cut -d" " -f1)
second_parent=$(git log --pretty=%P -n 1 | cut -d" " -f2)

commits=$(git log --pretty=format:'%h - %s' --abbrev-commit "${first_parent}..${second_parent}")
echo "$commits"

if echo "$commits" | grep "$WIP_MARKER" --quiet; then
    echo "ERROR: found the '$WIP_MARKER' marker in the PR commits..."
    exit 1
fi
