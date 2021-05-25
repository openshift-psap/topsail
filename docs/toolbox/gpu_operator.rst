============
GPU Operator
============

Deployment
==========

* Deploy from OperatorHub

.. code-block:: shell

    toolbox/gpu-operator/deploy_from_operatorhub.sh [<version>] [<channel>]
    toolbox/gpu-operator/undeploy_from_operatorhub.sh

**Examples:**

- ``./toolbox/gpu-operator/deploy_from_operatorhub.sh``

  - Installs the latest version available

- ``./toolbox/gpu-operator/deploy_from_operatorhub.sh 1.7.0 v1.7``

  - Installs ``v1.7.0`` from the ``v1.7`` channel

- ``./toolbox/gpu-operator/deploy_from_operatorhub.sh 1.6.2 stable``

  - Installs ``v1.6.2`` from the ``stable`` channel

**Note about the GPU Operator channel:**

- Before ``v1.7.0``, the GPU Operator was using a unique channel name
  (``stable``). Within this channel, OperatorHub would automatically
  upgrade the operator to the latest available version. This was an
  issue as the operator doesn't support (yet) being upgraded (remove
  and reinstall is the official way). OperatorHub allows specifying
  the upgrade as ``Manual``, but this isn't the default behavior.
- Starting with ``v1.7.0``, the channel is set to ``v1.7``, so that
  OperatorHub won't trigger an automatic upgrade.
- See the `OpenShift Subscriptions and channel documentation`_ for
  further information.

.. _OpenShift Subscriptions and channel documentation: https://docs.openshift.com/container-platform/4.7/operators/understanding/olm/olm-understanding-olm.html#olm-subscription_olm-understanding-olm

* List the versions available from OperatorHub

(not 100% reliable, the connection may timeout)

.. code-block:: shell

    toolbox/gpu-operator/list_version_from_operator_hub.sh

**Usage:**

.. code-block:: shell

    toolbox/gpu-operator/list_version_from_operator_hub.sh [<package-name> [<catalog-name>]]
    toolbox/gpu-operator/list_version_from_operator_hub.sh --help

*Default values:*

.. code-block:: shell

    package-name: gpu-operator-certified
    catalog-name: certified-operators
    namespace: openshift-marketplace (controlled with NAMESPACE environment variable)


* Deploy from NVIDIA helm repository

.. code-block:: shell

    toolbox/gpu-operator/list_version_from_helm.sh
    toolbox/gpu-operator/deploy_from_helm.sh <helm-version>
    toolbox/gpu-operator/undeploy_from_helm.sh


* Deploy from a custom commit.

.. code-block:: shell

    toolbox/gpu-operator/deploy_from_commit.sh <git repository> <git reference> [gpu_operator_image_tag_uid]

**Example:**

.. code-block:: shell

    toolbox/gpu-operator/deploy_from_commit.sh https://github.com/NVIDIA/gpu-operator.git master

Configuration
=============

* Set a custom repository list to use in the GPU Operator
  ``ClusterPolicy``

*Using a repo-list file*

.. code-block:: shell

   toolbox/gpu-operator/set_repo-config.sh /path/to/repo.list [dest-dir-in-pod]

**Default values**:

- *dest-dir-in-pod*: ``/etc/distro.repos.d``


Testing and Waiting
===================

* Wait for the GPU Operator deployment and validate it

.. code-block:: shell

    toolbox/gpu-operator/wait_deployment.sh


* Run `GPU-burn_` to validate that all the GPUs of all the nodes can
  run workloads

.. code-block:: shell

    toolbox/gpu-operator/run_gpu_burn.sh [gpu-burn runtime, in seconds]

**Default values:**

.. code-block:: shell

  gpu-burn runtime: 30

.. _GPU-burn: https://github.com/openshift-psap/gpu-burn


Troubleshooting
===============

* Capture GPU operator possible issues

(entitlement, NFD labelling, operator deployment, state of resources
in gpu-operator-resources, ...)

.. code-block:: shell

    toolbox/entitlement/test_cluster.sh
    toolbox/nfd/has_nfd_labels.sh
    toolbox/nfd/has_gpu_nodes.sh
    toolbox/gpu-operator/wait_deployment.sh
    toolbox/gpu-operator/run_gpu_burn.sh 30
    toolbox/gpu-operator/capture_deployment_state.sh


or all in one step:

.. code-block:: shell

    toolbox/gpu-operator/diagnose.sh

or with the must-gather script:

.. code-block:: shell

    toolbox/gpu-operator/must-gather.sh

or with the must-gather image:

.. code-block:: shell

    oc adm must-gather --image=quay.io/openshift-psap/ci-artifacts:latest --dest-dir=/tmp/must-gather -- gpu-operator_gather


Cleaning Up
===========

* Uninstall and cleanup stalled resources

``helm`` (in particular) fails to deploy when any resource is left from
a previously failed deployment, eg:

.. code-block::

    Error: rendered manifests contain a resource that already
    exists. Unable to continue with install: existing resource
    conflict: namespace: , name: gpu-operator, existing_kind:
    rbac.authorization.k8s.io/v1, Kind=ClusterRole, new_kind:
    rbac.authorization.k8s.io/v1, Kind=ClusterRole

.. code-block::

    toolbox/gpu-operator/cleanup_resources.sh
