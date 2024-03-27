============
GPU Operator
============

Deployment
==========

* Deploy from OperatorHub

.. code-block:: shell

    ./run_toolbox.py gpu_operator deploy_from_operatorhub [--version=<version>] [--channel=<channel>] [--installPlan=Automatic|Manual]
    ./run_toolbox.py gpu_operator undeploy_from_operatorhub

**Examples:**

- ``./run_toolbox.py gpu_operator deploy_from_operatorhub``

  - Installs the latest version available

- ``./run_toolbox.py gpu_operator deploy_from_operatorhub --version=1.7.0 --channel=v1.7``

  - Installs ``v1.7.0`` from the ``v1.7`` channel

- ``./run_toolbox.py gpu_operator deploy_from_operatorhub --version=1.6.2 --channel=stable``

  - Installs ``v1.6.2`` from the ``stable`` channel

- ``./run_toolbox.py gpu_operator deploy_from_operatorhub --installPlan=Automatic``

  - Forces the install plan approval to be set to ``Automatic``.

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

    ./run_toolbox.py gpu_operator deploy_from_commit <git repository> <git reference> [--tag_uid=TAG_UID]

**Example:**

.. code-block:: shell

    ./run_toolbox.py gpu_operator deploy_from_commit https://github.com/NVIDIA/gpu-operator.git master

Configuration
=============

* Set a custom repository list to use in the GPU Operator
  ``ClusterPolicy``

*Using a repo-list file*

.. code-block:: shell

   ./run_toolbox.py gpu_operator set_repo_config /path/to/repo.list [--dest_dir=DEST_DIR]

**Default values**:

- *dest-dir-in-pod*: ``/etc/distro.repos.d``


Testing and Waiting
===================

* Wait for the GPU Operator deployment and validate it

.. code-block:: shell

    ./run_toolbox.py gpu_operator wait_deployment


* Run `GPU-burn_` to validate that all the GPUs of all the nodes can
  run workloads

.. code-block:: shell

    ./run_toolbox.py gpu_operator run_gpu_burn [--runtime=RUNTIME, in seconds]

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

    ./run_toolbox.py entitlement test_cluster
    ./run_toolbox.py nfd has_labels
    ./run_toolbox.py nfd has_gpu_nodes
    ./run_toolbox.py gpu_operator wait_deployment
    ./run_toolbox.py gpu_operator run_gpu_burn --runtime=30
    ./run_toolbox.py gpu_operator capture_deployment_state


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
