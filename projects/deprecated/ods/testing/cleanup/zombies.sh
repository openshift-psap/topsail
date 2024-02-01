#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

TESTING_ODS_CLEANUP_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
source "$TESTING_ODS_CLEANUP_DIR/../configure.sh"

main() {
    "$TESTING_ODS_DIR/ci_init_configure.sh"

    if [[ "${INSIDE_CI_IMAGE:-}" == "y" ]]; then
        export AWS_SHARED_CREDENTIALS_FILE="${PSAP_ODS_SECRET_PATH:-}/.awscred"
        export AWS_CONFIG_FILE=/tmp/awccfg

        cat <<EOF > $AWS_CONFIG_FILE
[$AWS_DEFAULT_PROFILE]
output=text
EOF
    fi

    DELETE_FILE="$ARTIFACT_DIR/clusters_to_delete"

    touch "$DELETE_FILE"
    for region in $((get_config clusters.create.ocp.region; get_config clusters.create.ocp.region) | uniq);
    do
        python3 ./subprojects/cloud-watch/cleanup-rhods-zombie.py \
                --regions "$region" \
                --ci-prefix "$(get_config clusters.create.name_prefix)" \
                --ci-delete-older-than "$(get_config clusters.cleanup.max_age)" \
                --delete |& tee -a "$ARTIFACT_DIR/cleanup-rhods-zombie_1.$region.log"

        python3 ./subprojects/cloud-watch/ec2.py \
                --regions "$region" \
                --ci-prefix "$(get_config clusters.create.name_prefix)" \
                --ci-list-older-than "$(get_config clusters.cleanup.max_age)" \
                --ci-list-file "$DELETE_FILE" |& tee -a "$ARTIFACT_DIR/scan-ec2-instances.$region.log"
    done

    cluster_count=$(cat "$DELETE_FILE" | wc -l)
    echo "Found  $cluster_count clusters to delete:"
    cat "$DELETE_FILE"

    while read line
    do
        region=$(echo "$line" | cut -d" " -f1)
        cluster_id=$(echo "$line" | cut -d" " -f2);

        ./run_toolbox.py cluster destroy_ocp "$region" "$cluster_id"
    done < "$DELETE_FILE"

    for region in $((echo $OCP_REGION; echo $OSD_REGION) | uniq);
    do
        python3 ./subprojects/cloud-watch/cleanup-rhods-zombie.py \
                --regions "$region" \
                --ci-prefix "$(get_config clusters.create.name_prefix)" \
                --ci-list-older-than "$(get_config clusters.cleanup.max_age)" \
                --delete |& tee -a "$ARTIFACT_DIR/cleanup-rhods-zombie_2.$region.log"
    done

    return "$cluster_count" # exit with an error if some clusters have been deleted
}

main "$@"
