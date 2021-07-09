==============================
Node Feature Discover Operator
==============================

Deployment
==========

* Deploy the NFD operator from OperatorHub, and control the install
  channel

.. code-block:: shell

    ./run_toolbox.py nfd_operator deploy_from_operatorhub [--channel=CHANNEL, eg: 4.7]
    ./run_toolbox.py nfd_operator undeploy_from_operatorhub

Testing and Waiting
===================

* Test NFD deployment

(search for ``feature.node.kubernetes.io/system-os_release.ID=rhcos``
label)

.. code-block:: shell

    ./run_toolbox.py nfd has_labels

* Test with NFD if NVIDIA GPU nodes are available

Search for these NVIDIA GPU PCI labels (that's the labels used by the `GPU Operator`_):

.. _GPU Operator: https://github.com/NVIDIA/gpu-operator/blob/bf20acd6717324cb4cf333ca9c8ffe8a33a70086/controllers/state_manager.go#L35

.. code-block:: shell

    feature.node.kubernetes.io/pci-10de.present
    feature.node.kubernetes.io/pci-0302_10de.present
    feature.node.kubernetes.io/pci-0300_10de.present

.. code-block:: shell

    ./run_toolbox.py nfd has_gpu_nodes

* Wait with NFD for GPU nodes to become available

.. code-block:: shell

    ./run_toolbox.py nfd wait_gpu_nodes

* Deploy NFD Operator from its master branch

.. code-block:: shell

    ./run_toolbox.py nfd_operator deploy_from_commit <repo> <ref> [tag]

Example:

.. code-block:: shell

    ./run_toolbox.py nfd_operator deploy_from_commit https://github.com/openshift/cluster-nfd-operator.git master

End-to-end Testing
==================

* Test NFD Operator from its master branch

.. code-block:: shell

    ./run_toolbox.py local_ci deploy "run nfd-operator test_master_branch" https://github.com/openshift-psap/ci-artifacts master


Cleaning Up
===========

* Uninstall and cleanup NFD labels

.. code-block::

    ./run_toolbox.py nfd_operator undeploy_from_operatorhub
