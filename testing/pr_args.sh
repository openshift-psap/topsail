#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o errtrace

DEST=${1:-}

if [[ -z "$DEST" ]]; then
    echo "ERROR: expected a destination file as parameter ..."
    exit 1
fi

if [[ -z "${PULL_NUMBER:-}" ]]; then
    echo "ERROR: no PULL_NUMBER available ..."
    exit 1
fi

PR_URL="https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/pulls/$PULL_NUMBER"
PR_COMMENTS_URL="https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/issues/$PULL_NUMBER/comments"

author=$(echo "$JOB_SPEC" | jq -r .refs.pulls[0].author)

JOB_NAME_PREFIX=pull-ci-${REPO_OWNER}-${REPO_NAME}-${PULL_BASE_REF}
test_name=$(echo "$JOB_NAME" | sed "s/$JOB_NAME_PREFIX-//")

pr_json=$(curl -sSf "$PR_URL")
pr_body=$(jq -r .body <<< "$pr_json")
pr_comments=$(jq -r .comments <<< "$pr_json")
COMMENTS_PER_PAGE=30 # default
last_comment_page=$(($pr_comments / $COMMENTS_PER_PAGE))
[[ $(($pr_comments % $COMMENTS_PER_PAGE)) != 0 ]] && last_comment_page=$(($last_comment_page + 1))



last_user_test_comment=$(curl -sSf "$PR_COMMENTS_URL?page=$last_comment_page" \
                             | jq '.[] | select(.user.login == "'$author'") | .body' \
                             | (grep "$test_name" || true) \
                             | tail -1 | jq -r)

if [[ -z "$last_user_test_comment" ]]; then
    echo "WARNING: last comment of author '$author' could not be found ..."
fi

pos_args=$(echo "$last_user_test_comment" |
               (grep "$test_name" || true) | cut -d" " -f3- | tr -d '\n' | tr -d '\r')
if [[ "$pos_args" ]]; then
    echo "PR_POSITIONAL_ARGS='$pos_args'" >> "$DEST"
    i=0
    for pos_arg in $pos_args; do
        echo "PR_POSITIONAL_ARG_$i='$pos_arg'" >> "$DEST"
        i=$((i + 1))
    done
fi

while read line; do
    [[ $line != "/var "* ]] && continue
    [[ $line != *=* ]] && continue

    key=$(echo "$line" | cut -d" " -f2- | cut -d= -f1)
    value=$(echo "$line" | cut -d= -f2 | tr -d '\n' | tr -d '\r')

    echo "$key='$value'" >> "$DEST"
done <<< $(echo "$pr_body"; echo "$last_user_test_comment")
