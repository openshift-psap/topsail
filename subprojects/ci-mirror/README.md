# Entitled Mirror
This directory contains Containerfiles and an OpenShift template for deploying mirrors to be used by the ci-artifacfts CI. 

These mirrors include:
- An entitled yum package repository mirror (files retrieved with yum `reposync`) to facilitate driver compilation on CI clusters.
- AI training and inference datasets mirror - for now it contains a few datasets from [coco](https://cocodataset.org/#download).

## Overview
The mirrors cluster is expected to only be deployed once and run indefinitely for use by CI clusters.

## Prerequisites
- An OpenShift cluster
- A CA certificate which you can generate client certificates from. Follow `../auth/README.md` for more information, scripts and examples.
```bash
mkdir generated_auth
pushd generated_auth
../../auth/all.sh
cp ../../auth/**/generated* .
popd
```
- The github.com/openshift-psap forked openshift-acme controller (see `./deploy_acme.sh`) must be running on the cluster
```bash
for mirror in $(ls mirrors); do
    . ./mirrors/${mirror}/config.env
    ./deploy_acme.sh
done
```
- At least one entitled (SKU MCT2741F3) Node with label `entitled="true"`. This requirement is also for mirrors that don't actually need entitlement, because of OpenShift template limitations (can't conditionally choose whether to add a nodeSelector to a pod in the template).
```bash
# Entitle a node, then set its name here:
oc get nodes
NODE=<node_name>
oc label node/$NODE entitled=true
```

# Cluster Architecture
Each mirror consists of multiple CRs deployed via an OpenShift template. Each mirror resides in its own namespace.
These CRs include: (you may need to read further sections in this README to understand all of it)
- A namespace, to contain all the mirror CRs.
- A Route + Service to make it publicly accessible. The route is annotated to be managed by openshift-acme in order to generate TLS cert and key
- A PersistentVolumeClaim to store mirror data
- A ServiceAccount and SecurityContextConstraints to make sure node entitlements come through to the entitled-yum mirror sync pod. Cluster-scoped, but relevant only for the entitled-yum mirror.
- A Secret to hold the client-ca certificate in order to authenticate clients
- A ConfigMap to hold the NGINX configuration file
- A ConfigMap to hold the script used by the sync container to download the mirror files. This script must be idempotent to avoid re-downloading after a pod restart.
- A Deployment with a pod template consisting of the the sync containiner as an initContainer and the serve container as a regular container

## Mirror configuration files
The differences between each mirror are encoded in the `mirrors` subdirectory.

mirrors
├── .nginx-default.conf # A default NGINX configuration file to be used by the mirrors
├── dataset
│   ├── config.env # The parameters for the dataset repo
│   └── sync.sh # The sync script for the dataset mirror
└── entitled-yum
    ├── config.env # The parameters for the entitled-yum repo
    ├── sync.sh # The sync script for the entitled-yum mirror
    └── yum.repo.d
        └── rhods_mirror.repo # An example `yum` repo configuration file to make use of the entitled yum mirror.

## Containers
Each mirror deployment makes use of two container images:
- The `sync` init container, hosted in `${QUAY_REPO}:sync`. This container is responsible for downloading all the data required to be served by the mirror
- The `serve` container, hosted in `${QUAY_REPO}:serve`. This container is responsible for running the NGINX server to serve the contents synced by the init container.

To build & push new versions of the containers images, `podman login` to your quay.io account (which must be authorized to push to the `openshift-psap` organization) and run `./containers/build.sh` to build and `./containers/upload.sh` to push. This must be done for each of the mirrors:
```bash
for mirror in $(ls mirrors); do
    . ./mirrors/${mirror}/config.env
    ./containers/build.sh
    ./containers/upload.sh
done
```

## TLS mutual authentication
Typically TLS (HTTPS) is only deployed to authenticate the server, but in our mirror deployment we also authenticate the client because we don't want the mirror content to be publicly available. The `serve` container is (see "Containers" section) configured to perform both authentications.
- Server authentication certificate generation is handled by the acme controller (see "Prerequisites") using LetsEncrypt.
- Client authentication certificate generation is handled by the `auth` directory inside this directory, see the README.md inside of it for more information. 

## Storage
The OpenShift template `openshift/template.yaml` defines a persistent volume claim for enough storage to store all the mirror packages. It makes use of the cluster's default StorageClass.

# Installation
## Initial deployment
- Make sure your KUBECONFIG points to the correct cluster on which you wish to deploy the mirror
- Source the configuration file for 
- Run `./deploy.sh` (note that this will launch a pod that will begin syncing all the repos defined in `containers/sync/sync_commands.sh`)
 into a mounted volume
- Follow the logs of the deployment containers to make sure everything is operating correctly

Example on how to deploy & wait for all mirrors:
```bash
# Deploy all mirrors
for mirror in $(ls mirrors); do
    source ./mirrors/${mirror}/config.env

    echo Deploying mirror $mirror

    # Deploy mirror
    ./deploy.sh
done

# Sleep for a bit
sleep 10

for mirror in $(ls mirrors); do
    source ./mirrors/${mirror}/config.env

    echo Waiting for $mirror to deploy

    # Wait for the end of the repo mirror synchronization, > 15min
    oc logs -f deployments/${NAME} -c sync -n ${NAMESPACE}

    # Check that the mirror is accessible and the credentials work
    MIRROR_HOSTNAME=$(oc get route/${NAME} -n ${NAMESPACE} '-ojsonpath={.status.ingress[0].host}')
    TEST_URL="https://${MIRROR_HOSTNAME}/healthy"
    if ! curl --silent --cert generated_auth/generated_client_creds.pem ${TEST_URL} --fail > /dev/null; then
        echo "Failed to access ${TEST_URL}"
    else
        echo "${MIRROR_HOSTNAME} seems healthy"
    fi
done
```

## Redeployment
After making changes, you may wish to -
- Re-build & re-upload the containers - see the "Containers" section.
- `./delete.sh` - Delete all the the template CRs. Note that this intentionally avoids deleting the PVC because syncing all the repositories take a really long time. If you wish to also delete the PVC, use `delete_pvc.sh`.
- `./deploy.sh` - Deploy the OpenShift template. See "Initial deployment".
- `./cycle.sh` - Does all of the above, in that order (without deleting the PVC).

# Directory map
```
.
├── cycle.sh # See the "Redeployment" section above
├── delete_pvc.sh # See the "Redeployment" section above
├── delete.sh # See the "Redeployment" section above
├── deploy_acme.sh # See the "Prerequisites" section above
├── deploy.sh # See the "Initial deployment" section above
├── containers # See the "Containers" section above
│   └── ...
├── mirrors # See the "Mirror configuration files" section above
│   └── ...
├── openshift
│   └── template.yaml # An OpenShift template containing all the required CRs for a mirror.
└── README.md
```
