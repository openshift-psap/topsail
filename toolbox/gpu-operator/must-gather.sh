#! /bin/bash -e

if [[ "$0" == "/usr/bin/gpu-operator_gather" ]]; then
    echo "Running as must-gather plugin image"
    export ARTIFACT_DIR=/must-gather

    TOP_DIR="$(dirname "$(readlink -f "$0")")/../../"
else
    THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

    # avoid sourcing _common.sh and messing up different env variables
    export TOOLBOX_SCRIPT_NAME=$0

    COMMON_SH=$(
        bash -c 'source '$THIS_DIR'/../_common.sh;
                 echo "8<--8<--8<--";
                 # only evaluate these variables from _common.sh
                 echo TOP_DIR=$(pwd)
                 env | egrep "(^ARTIFACT_EXTRA_LOGS_DIR=|^ARTIFACT_DIR=)"'
             )
    echo "$COMMON_SH" | sed '/8<--8<--8<--/Q'
    ENV=$(echo "$COMMON_SH" | tac | sed '/8<--8<--8<--/Q' | tac) # keep only what's after the 8<--

    echo "Setting env values:"
    echo "$ENV"
    eval $ENV
fi

cd $TOP_DIR

MUST_GATHER_LOGS_DIR="$ARTIFACT_DIR"
MUST_GATHER_INSPECT_DIR="$ARTIFACT_DIR/oc_adm_inspect"

exec 1> >(tee $MUST_GATHER_LOGS_DIR/_must-gather.log)
exec 2> >(tee $MUST_GATHER_LOGS_DIR/_must-gather.stderr.log >&2)

set -x

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
