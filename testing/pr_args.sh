#! /bin/bash -xe

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
    echo "ERROR: no PR_NUMBER available ..."
    exit 1
fi

PR_URL="https://api.github.com/repos/openshift-psap/ci-artifacts/pulls/$PULL_NUMBER"
PR_COMMENTS_URL="https://api.github.com/repos/openshift-psap/ci-artifacts/issues/$PULL_NUMBER/comments"

author=kpouget #;$(echo "$JOB_SPEC" | jq -r .refs.pulls[0].author)

JOB_NAME_PREFIX=pull-ci-openshift-psap-ci-artifacts-master
test_name=test-pr-no-cluster #$(echo "$JOB_NAME" | sed "s/$JOB_NAME_PREFIX-//")

last_user_test_comment=$(curl -sSf "$PR_COMMENTS_URL" \
                             | jq '.[] | select(.user.login == "'$author'") | .body' \
                             | grep "$test_name" \
                             | tail -1 | jq -r)
pr_body=$(curl -sSf $PR_URL | jq -r .body)

pos_args=$(echo "$last_user_test_comment" |
               grep "$test_name" | cut -d" " -f3- | tr -d '\n' | tr -d '\r')
if [[ "$pos_args" ]]; then
    echo "PR_POSITIONAL_ARGS='$pos_args'" >> "$DEST"
fi

while read line; do
    [[ $line != "/env "* ]] && continue
    [[ $line != *=* ]] && continue

    key=$(echo "$line" | cut -d" " -f2- | cut -d= -f1)
    value=$(echo "$line" | cut -d= -f2 | tr -d '\n' | tr -d '\r')

    echo "$key='$value'" >> "$DEST"
done <<< $(echo "$pr_body"; echo "$last_user_test_comment")
