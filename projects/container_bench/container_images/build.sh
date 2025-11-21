#!/bin/bash

# usage:
# REGISTRY=quay.io NAMESPACE=myorg VERSION=v1.0 ./build.sh

set -e

REGISTRY="${REGISTRY:-quay.io}"
NAMESPACE="${NAMESPACE:-jrodak}"
VERSION="${VERSION:-latest}"

if ! command -v podman &> /dev/null; then
    echo "ERROR: podman not found. Please install podman."
    exit 1
fi

IMAGES=("sysbench" "iperf3")

build_image() {
    local image_name=$1
    local containerfile="Containerfile.${image_name}"
    local image_tag="${REGISTRY}/${NAMESPACE}/${image_name}:${VERSION}"

    echo "Building ${image_name} for amd64 and arm64..."

    podman manifest create "${image_tag}" || true

    podman build \
        --platform linux/amd64 \
        --manifest "${image_tag}" \
        -f "${containerfile}" \
        -t "${image_tag}-amd64" \
        .

    podman build \
        --platform linux/arm64 \
        --manifest "${image_tag}" \
        -f "${containerfile}" \
        -t "${image_tag}-arm64" \
        .

    echo "Successfully built ${image_name}"
}

echo "Registry: ${REGISTRY}"
echo "Namespace: ${NAMESPACE}"
echo "Version: ${VERSION}"
echo ""

for image in "${IMAGES[@]}"; do
    if [ ! -f "Containerfile.${image}" ]; then
        echo "WARNING: Containerfile.${image} not found, skipping..."
        continue
    fi
    build_image "$image"
    echo ""
done

echo "Build process completed!"
echo ""
echo "Local images built. To push them, run:"
for image in "${IMAGES[@]}"; do
    echo "  podman manifest push ${REGISTRY}/${NAMESPACE}/${image}:${VERSION}"
done

