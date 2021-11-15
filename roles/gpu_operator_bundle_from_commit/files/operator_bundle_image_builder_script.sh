#! /bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -x

LOCAL_OPERATOR_IMAGE_REPOSITORY="image-registry.openshift-image-registry.svc:5000/gpu-operator-ci"
LOCAL_OPERATOR_IMAGE_NAME="gpu-operator-ci"

echo "QUAY_BUNDLE_IMAGE_NAME=${QUAY_BUNDLE_IMAGE_NAME}"

if [ "${PUBLISH_TO_QUAY:-}" ]; then
    if [ "${WITH_DRIVER:-}" ]; then
        echo "FATAL: Cannot have PUBLISH_TO_QUAY and WITH_DRIVER enabled together."
        exit 1
    fi

    OPERATOR_IMAGE_REPOSITORY="$(dirname "$QUAY_BUNDLE_IMAGE_NAME")"
    OPERATOR_IMAGE_NAME="$(basename "$QUAY_BUNDLE_IMAGE_NAME")"
else
    OPERATOR_IMAGE_REPOSITORY="${LOCAL_OPERATOR_IMAGE_REPOSITORY}"
    OPERATOR_IMAGE_NAME="${LOCAL_OPERATOR_IMAGE_NAME}"
fi

BUNDLE_IMAGE_FULL="${QUAY_BUNDLE_IMAGE_NAME}:operator_bundle_${OPERATOR_IMAGES_TAG_SUFFIX}"

CONTAINER_FILE=./docker/bundle.Dockerfile

CONTEXT_LOCATION="."

CSV_FILE=bundle/manifests/gpu-operator.clusterserviceversion.yaml

(echo "{ \"auths\": " ; cat /var/run/secrets/openshift.io/push/.dockercfg ; echo "}") > /tmp/.dockercfg_local
LOCAL_AUTH="--tls-verify=false --authfile /tmp/.dockercfg_local"

cat /var/run/secrets/quay.io/push/.dockerconfigjson > /tmp/.dockercfg_quay
QUAY_AUTH="--tls-verify=false --authfile /tmp/.dockercfg_quay"

# ---

replace_related_image() {
    NAME=$1
    shift
    NEW_IMAGE=$1

    echo "Patching ${CSV_FILE} ${NAME} related image to ${NEW_IMAGE}"

    yq '.spec.relatedImages = [
    .spec.relatedImages[] |
    if (.name == "'${NAME}'") then
        .image = "'${NEW_IMAGE}'"
    else
        .
    end
    ]' ${CSV_FILE} --yaml-output --in-place
}

get_image_sha() {
    local_img=$1

    podman pull --quiet $LOCAL_AUTH "$local_img" > /dev/null

    SHA=$(podman inspect "$local_img" | jq -r .[].Digest)

    echo "$(echo $local_img | cut -d: -f1)@${SHA}"
}

push_to_quay() {
    local_img=$1
    dest_img="${QUAY_BUNDLE_IMAGE_NAME}:$(echo $local_img | cut -d: -f2)"

    # pull the images locally
    podman pull --quiet $LOCAL_AUTH "$local_img" > /dev/null
    # then push it to quay
    podman push --quiet $QUAY_AUTH "$local_img" "$dest_img" > /dev/null

    SHA=$(podman inspect "$local_img" | jq -r .[].Digest)

    echo "${dest_img}@${SHA}"
}

# ---

mkdir /work -p && cd /work

rm -rf gpu-operator

git clone ${OPERATOR_GIT_REPO} gpu-operator -b ${OPERATOR_GIT_REF} --depth 1

cd gpu-operator

git show --quiet
GIT_VERSION=$(git rev-parse --short HEAD)

DATE_VERSION=$(date -d "@$(git log -1 ${GIT_VERSION} --format="%at")" +%y.%-m.%-d) # gives 21.9.29
CSV_VERSION="${DATE_VERSION}-git.${GIT_VERSION}"

OPERATOR_IMAGE_VERSION="operator_${OPERATOR_IMAGES_TAG_SUFFIX}"

OPERATOR_LOCAL_IMAGE_FULL="${OPERATOR_IMAGE_REPOSITORY}/${OPERATOR_IMAGE_NAME}:${OPERATOR_IMAGE_VERSION}"

if [ "${PUBLISH_TO_QUAY:-}" ]; then
    OPERATOR_IMAGE=$(push_to_quay "${OPERATOR_LOCAL_IMAGE_FULL}")
else
    OPERATOR_IMAGE=$(get_image_sha "${OPERATOR_LOCAL_IMAGE_FULL}")
fi

replace_related_image "gpu-operator-image" "$OPERATOR_IMAGE"

cp "$CSV_FILE" "${CSV_FILE}.orig"

cat "${CSV_FILE}.orig" | yq \
    | jq '.metadata.annotations.containerImage="'${OPERATOR_IMAGE}'"' \
    | jq '.metadata.name="'gpu-operator-certified-${CSV_VERSION}'"' \
    | jq '.spec.version="'${CSV_VERSION}'"' \
    | jq '.spec.install.spec.deployments[0].spec.template.spec.containers[0].image="'$OPERATOR_IMAGE'"' \
         > $CSV_FILE

rm ${CSV_FILE}.orig

cat ${CSV_FILE} | yq \
    | jq '.metadata.annotations."alm-examples"' -r \
         > clusterpolicy.json

if [ "${WITH_VALIDATOR:-}" ]; then
    # update validator & node-status-exporter images in the ClusterPolicy
    VALIDATOR_IMAGE_VERSION="validator_${OPERATOR_IMAGES_TAG_SUFFIX}"
    VALIDATOR_LOCAL_IMAGE="${OPERATOR_IMAGE_REPOSITORY}/${OPERATOR_IMAGE_NAME}:${VALIDATOR_IMAGE_VERSION}"

    if [ "${PUBLISH_TO_QUAY:-}" ]; then
        VALIDATOR_IMAGE=$(push_to_quay "${VALIDATOR_LOCAL_IMAGE}")
    else
        VALIDATOR_IMAGE=$(get_image_sha "${VALIDATOR_LOCAL_IMAGE}")
    fi

    replace_related_image "gpu-operator-validator-image" "$VALIDATOR_IMAGE"

    VALIDATOR_IMAGE_VERSION_SHA=$(echo "$VALIDATOR_IMAGE" | cut -d@ -f2)

    mv clusterpolicy.json{,.orig}
    cat clusterpolicy.json.orig \
        | jq '.[].spec.validator.image="'${OPERATOR_IMAGE_NAME}'"' \
        | jq '.[].spec.validator.repository="'${OPERATOR_IMAGE_REPOSITORY}'"' \
        | jq '.[].spec.validator.version="'${VALIDATOR_IMAGE_VERSION_SHA}'"' \
             \
        | jq '.[].spec.nodeStatusExporter.image="'${OPERATOR_IMAGE_NAME}'"' \
        | jq '.[].spec.nodeStatusExporter.repository="'${OPERATOR_IMAGE_REPOSITORY}'"' \
        | jq '.[].spec.nodeStatusExporter.version="'${VALIDATOR_IMAGE_VERSION_SHA}'"' \
             > clusterpolicy.json
    rm  clusterpolicy.json.orig
fi

if [ "${WITH_DRIVER:-}" ]; then
    # update driver image in the ClusterPolicy

    DRIVER_LOCAL_IMAGE="${OPERATOR_IMAGE_REPOSITORY}/${OPERATOR_IMAGE_NAME}:driver_${OPERATOR_IMAGES_TAG_SUFFIX}"

    if [ "${PUBLISH_TO_QUAY:-}" ]; then
        DRIVER_IMAGE=$(push_to_quay "${DRIVER_LOCAL_IMAGE}")
    else
        DRIVER_IMAGE=$(get_image_sha "${DRIVER_LOCAL_IMAGE}")
    fi

    replace_related_image "driver-image" "$DRIVER_IMAGE"

    DRIVER_IMAGE_VERSION_SHA=$(echo "$DRIVER_IMAGE" | cut -d@ -f2)

    mv clusterpolicy.json{,.orig}
    cat clusterpolicy.json.orig \
        | jq '.[].spec.driver.image="'${OPERATOR_IMAGE_NAME}'"' \
        | jq '.[].spec.driver.repository="'${OPERATOR_IMAGE_REPOSITORY}'"' \
        | jq '.[].spec.driver.version="'${DRIVER_IMAGE_VERSION_SHA}'"' \
             > clusterpolicy.json
    rm  clusterpolicy.json.orig
else
    # TMP update driver image in the ClusterPolicy with Shiva's v1.9.0 build

    DRIVER_TMP_IMAGE="quay.io/shivamerla/driver:470.57.02-rhcos4.9"

    DRIVER_IMAGE=$(get_image_sha "$DRIVER_TMP_IMAGE")

    replace_related_image "driver-image" "$DRIVER_IMAGE"

    DRIVER_IMAGE_VERSION_SHA=$(echo "$DRIVER_IMAGE" | cut -d@ -f2)

    mv clusterpolicy.json{,.orig}
    cat clusterpolicy.json.orig \
        | jq '.[].spec.driver.image="driver"' \
        | jq '.[].spec.driver.repository="quay.io/shivamerla"' \
        | jq '.[].spec.driver.version="'$DRIVER_IMAGE_VERSION_SHA'"' \
             > clusterpolicy.json
    rm  clusterpolicy.json.orig
fi

# update ClusterPolicy in the CSV

mv "${CSV_FILE}" "${CSV_FILE}.orig"
yq --yaml-roundtrip --rawfile alm_examples clusterpolicy.json '.metadata.annotations."alm-examples" = $alm_examples' "${CSV_FILE}.orig" > "${CSV_FILE}"
rm "${CSV_FILE}.orig"
rm clusterpolicy.json

# build the bundle image

podman build -f "${CONTAINER_FILE}" "${CONTEXT_LOCATION}" -t "${BUNDLE_IMAGE_FULL}"

# push the bundle image to quay.io

# mandatory for now, the bundle image must be accessible from the whole cluster
# I couldn't find any way not involving storing the bundle image in quay.io

podman push $QUAY_AUTH "${BUNDLE_IMAGE_FULL}"
