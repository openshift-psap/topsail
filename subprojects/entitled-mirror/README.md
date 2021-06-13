# Entitled Mirror
This directory contains Containerfiles and an OpenShift template for deploying an entitled package repository mirror (using yum `reposync` and NGINX) to facilitate driver compilation on CI clusters.

## Overview
The mirror is expected to only be deployed once and run indefinitely for use by CI clusters.

## Prerequisites
- An OpenShift cluster
- At least one entitled (SKU MCT2741F3) Node with label `entitled="true"`
```bash
# Entitle a node, then set its name here:
NODE=<node_name>
oc label node/$NODE entitled=true
```
- A CA certificate which you can generate client certificates from. Follow `./auth/README.md` for more information, scripts and examples.
```bash
./auth/all.sh
```
- The github.com/openshift-psap forked openshift-acme controller (see `./deploy_acme.sh`) must be running on the cluster
```bash
./deploy_acme.sh
```

## Containers
The deployment makes use of two container images:
- The `sync` init container, hosted in `quay.io/openshift-psap/entitled-mirror:sync`. This container is responsible for running `reposync` for all the mirrored repositories to make sure they're ready for mirroring.
- The `serve` container, hosted in `quay.io/openshift-psap/entitled-mirror:serve`. This container is responsible for running the NGINX server to serve the contents synced by the init container.

To build & push new versions of the containers images, `podman login` to your quay.io account (which must be authorized to push to the `openshift-psap` organization) and run `./containers/build.sh` to build and `./containers/upload.sh` to push.

## TLS mutual authentication
Typically TLS (HTTPS) is only deployed to authenticate the server, but in our mirror deployment we also authenticate the client because we don't want the mirror content to be publicly available. The `serve` container is (see "Containers" section) configured to perform both authentications.
- Server authentication certificate generation is handled by the acme controller (see "Prerequisites") using LetsEncrypt.
- Client authentication certificate generation is handled by the `auth` directory inside this directory, see the README.md inside of it for more information. 

## Storage
The OpenShift template `openshift/template.yaml` defines a persistent volume claim for enough storage to store all the mirror packages. It makes use of the cluster's default StorageClass.

# Installation
## Initial deployment
- Make sure your KUBECONFIG points to the correct cluster on which you wish to deploy the mirror
- Run `./deploy.sh` (note that this will launch a pod that will begin syncing all the repos defined in `containers/sync/sync_commands.sh`)
 into a mounted volume
- Follow the logs of the deployment containers to make sure everything is operating correctly, e.g.:

```bash
# Load environment
. config.env

# Wait for the end of the repo mirror synchronization, > 15min
oc logs -f deployments/${NAME} -c reposync -n ${NAMESPACE}

# Check that the mirror is accessible and the credentials work
MIRROR_HOSTNAME=$(oc get route/${NAME} -n ${NAMESPACE} -ojsonpath={.status.ingress[0].host})
curl -E ./auth/client/generated_client_creds.pem ${MIRROR_HOSTNAME}/repodata/repomd.xml
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
├── auth # Contains TLS-client authentication scripts. See auth README.md for more information.
│   ├── all.sh
│   ├── ca
│   │   ├── csr.cnf
│   │   ├── gen_ca.sh
│   │   └── sign.sh
│   ├── client
│   │   ├── csr.cnf
│   │   └── gen_client.sh
│   ├── delete.sh
│   └── README.md
├── config.env # General configuration for the scripts in this directory
├── containers # See the "Containers" section above
│   ├── build.sh 
│   ├── upload.sh
│   ├── serve
│   │   ├── Containerfile.serve
│   │   └── nginx.conf # The nginx.conf file used by the serve container
│   └── sync
│       ├── Containerfile.sync
│       └── sync_commands.sh # The commands used to sync the repositories.
│                            # Also acts as a list of repositories synced by the mirror
├── cycle.sh # See the "Redeployment" section above
├── delete_pvc.sh # See the "Redeployment" section above
├── delete.sh # See the "Redeployment" section above
├── deploy_acme.sh # See the "Prerequisites" section above
├── deploy.sh # See the "Initial deployment" section above
├── openshift
│   └── template.yaml # An OpenShift template containing all the required CRs for the mirror.
├── README.md
└── yum.repo.d
    └── rhods_mirror.repo # An example `yum` repo configuration file to make use of the mirror.
```
