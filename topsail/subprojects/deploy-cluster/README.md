This repository provides a few helper commands to deploy an entitled
GPU OpenShift cluster. See [`Makefile`](Makefile) to understand what
the commands actually do.

Configuration
-------------

Copy [`utils/config.mk.sample`](utils/config.mk.sample) into
`utils/config.mk`, then edit it to customize the installation
properties:

```
TODAY ?= $(shell date '+%Y%m%d')
CLUSTER_NAME ?= ${USER}-${TODAY}
CLUSTER ?= ${PWD}/clusters/${CLUSTER_NAME}

ENTITLEMENT_PEM ?= /path/to/entitlement.pem

OCP_VERSION ?= 4.7
OPENSHIFT_INSTALLER ?= ${UTILS_DIR}/installers/${OCP_VERSION}/openshift-install
```

Commands
--------

```
config_new_install|config_base_install -> manifest -> manitest_entitle -> install -> kubeconfig -> uninstall -> cleanup
```

## `make config_new_install`

Creates the cluster's `install-config.yaml` with the assistant `openshift-install
create install-config`.

To have worker nodes with a GPU, use this machine-type
`compute[0].platform.aws.type = g4dn.xlarge` :

```
compute:
- architecture: amd64
  hyperthreading: Enabled
  name: worker
  platform:
   aws:
     type: g4dn.xlarge
  replicas: 2
```

## `make config_base_install`

Uses `${BASE_INSTALL_CONFIG}` `install-config.yaml` template
([see my sample](utils/install-config.yaml.sample)) to create a new
cluster with the same properties as the template, but a different name
(`${CLUSTER_NAME}`). Then launches `${DIFF_TOOL}` to compare the
template and the actual `install-config.yaml` file.

## `make manifest`

Generates `${CLUSTER_PATH}/openshift` directory. This directory contains
the resources to create when the OCP cluster is spawned. Mind that
multi-document YAML files (with `---`) are not supported here (only
the first document is created) (with OCP `4.6.12`).

## `make manifest_entitle`

Generates the entitlement manifest files from

1. the [template file](utils/cluster-wide.entitlement.machineconfigs.yaml.template)
2. the PEM file at `${ENTITLEMENT_PEM}`.
3. the RHSM file at [`utils/rhsm.conf`](utils/rhsm.conf)

## `make install`

Creates the OpenShift cluster.

## `make kubeconfig`

Prints out the `KUBECONFIG` to export to use the current cluster.

## `make uninstall`

Destroys the OpenShift cluster.

---

## `make cluster`

Equivalent of:

```
	make config_base_install
	make manifest
	make manifest_entitle
	make install
	make kubeconfig
```

## `make cluster_light`

Equivalent of

```
	make config_base_install
	make config_single-master
	make manifest
	make manifest_entitle
	make manifest_single-master
	make install
	make kubeconfig
```

