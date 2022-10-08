#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

if [[ "${INSIDE_CI_IMAGE:-}" == "y" ]]; then
    export AWS_DEFAULT_PROFILE=${AWS_DEFAULT_PROFILE:-ci-artifact}
    export AWS_SHARED_CREDENTIALS_FILE="${PSAP_ODS_SECRET_PATH:-}/.awscred"
    export AWS_CONFIG_FILE=/tmp/awccfg

    cat <<EOF > $AWS_CONFIG_FILE
[$AWS_DEFAULT_PROFILE]
output=text
EOF
fi

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

source "$THIS_DIR/config_common.sh"
source "$THIS_DIR/config_clusters.sh"

DELETE_FILE="$ARTIFACT_DIR/clusters_to_delete"

touch "$DELETE_FILE"
for region in $((echo $OCP_REGION; echo $OSD_REGION) | uniq);
do
    python3 ./subprojects/cloud-watch/cleanup-rhods-zombie.py \
            --regions "$region" \
            --ci-prefix "$CLUSTER_NAME_PREFIX" \
            --ci-delete-older-than "$CLUSTER_CLEANUP_DELAY" \
            --delete |& tee -a "$ARTIFACT_DIR/cleanup-rhods-zombie_1.$region.log"

    python3 ./subprojects/cloud-watch/ec2.py \
            --regions "$region" \
            --ci-prefix "$CLUSTER_NAME_PREFIX" \
            --ci-list-older-than "$CLUSTER_CLEANUP_DELAY" \
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
            --ci-prefix "$CLUSTER_NAME_PREFIX" \
            --ci-delete-older-than "$CLUSTER_CLEANUP_DELAY" \
            --delete |& tee -a "$ARTIFACT_DIR/cleanup-rhods-zombie_2.$region.log"
done

exit "$cluster_count" # exit with an error if some clusters have been deleted
