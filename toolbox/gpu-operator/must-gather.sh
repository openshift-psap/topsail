#! /bin/bash -ex

if [[ "$0" == "/usr/bin/gpu-operator_gather" ]]; then
    echo "Running as must-gather plugin image"
    export ARTIFACT_DIR=/must-gather

    THIS_DIR="$(dirname "$(readlink -f "$0")")"
else
    # avoid sourcing _common.sh and messing up different env variables
    if [[ -z "${ARTIFACT_DIR:-}" ]]; then
        export ARTIFACT_DIR="/tmp/ci-artifacts_$(date +%Y%m%d)"
        echo "Using '$ARTIFACT_DIR' to store the test artifacts (default value for ARTIFACT_DIR)."
    else
        echo "Using '$ARTIFACT_DIR' to store the test artifacts."
    fi

    export ARTIFACT_DIR="$ARTIFACT_DIR/$(date +%H%M%S)__gpu-operator__must-gather"
    THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
fi

mkdir -p "$ARTIFACT_DIR"
cd $THIS_DIR/../../

MUST_GATHER_LOGS_DIR="$ARTIFACT_DIR"
MUST_GATHER_INSPECT_DIR="$ARTIFACT_DIR/oc_adm_inspect"

exec 1> >(tee $MUST_GATHER_LOGS_DIR/_must-gather.log)
exec 2> >(tee $MUST_GATHER_LOGS_DIR/_must-gather.stderr.log >&2)

# product
cat <<EOF > $MUST_GATHER_LOGS_DIR/version
ci-artifacts/toolbox/gpu-operator/must-gather
$(git describe HEAD --long --always)
EOF

git show -s > $MUST_GATHER_LOGS_DIR/version.git_commit

# Named resource list, eg. ns/openshift-config
named_resources=()
named_resources+=(ns/gpu-operator-resources)
named_resources+=(ns/openshift-nfd)

echo "# resources to inspect: ${named_resources[@]}"

for named_res in "${named_resources[@]}"; do
    # Run the Collection of Resources using inspect
    oc adm inspect --dest-dir=$MUST_GATHER_INSPECT_DIR $named_res -n default || true
done

for res_type in InstallPlan ClusterServiceVersion; do
    while read line; do
        name=$res_type/$(echo "$line" | awk '{ print $2 }')
        ns=$(echo "$line" | awk '{ print $1 }')
        if [[ "$ns" != openshift-nfd && "$ns" != openshift-operators ]]; then
            echo "# skip '$name -n $ns' (not interested in this namespace)"
            continue
        fi
        echo "# $res_type to inspect: $name -n $ns"
        oc adm inspect --dest-dir=$MUST_GATHER_INSPECT_DIR $name -n $ns || true
    done <<< $(oc get --no-headers $res_type -A | egrep '(nfd|gpu-operator)')
done

for clusterpolicy_name in $(oc get clusterpolicy -oname || true); do
    echo "# clusterpolicy to inspect: $clusterpolicy_name"
    oc adm inspect --dest-dir=$MUST_GATHER_INSPECT_DIR $clusterpolicy_name || true
done

# ---

toolbox/gpu-operator/diagnose.sh \
    --run-all \
    1> >(tee $MUST_GATHER_LOGS_DIR/diagnose.log) \
    2> >(tee $MUST_GATHER_LOGS_DIR/diagnose.stderr.log >&2)

# ---
echo
echo
echo "All done! Results have been gathered in '$ARTIFACT_DIR'"
