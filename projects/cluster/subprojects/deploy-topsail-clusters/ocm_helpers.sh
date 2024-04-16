#! /bin/bash

cluster_helpers::ocm_login() {
    local ocm_env=$(get_config clusters.sutest.managed.env)

    # do it in a subshell to avoid leaking the `OCM_TOKEN` secret because of `set -x`
    bash -c '
      set -o errexit
      set -o nounset

      OCM_TOKEN=$(cat "'$PSAP_ODS_SECRET_PATH'/ocm.token" | grep "^'${ocm_env}'=" | cut -d= -f2-)
      echo "Login in '$ocm_env' with token length=$(echo "$OCM_TOKEN" | wc -c)"
      exec ocm login --token="$OCM_TOKEN" --url="'$ocm_env'"
      '
}
