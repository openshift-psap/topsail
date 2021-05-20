===========
Entitlement
===========


Deployment
==========

* Deploy the entitlement cluster-wide

Deploy a PEM key and RHSM configuration, and optionally, a custom CA
PEM file.

The custom CA file will be stored in
``/etc/rhsm-host/ca/custom-repo-ca.pem`` in the host and in
``/etc/rhsm/ca/custom-repo-ca.pem`` in the Pods.

.. code-block:: shell

    toolbox/entitlement/deploy.sh --pem /path/to/key.pem

* Undeploy the cluster-wide entitlement (PEM keys, RHSM configuration
  and custom CA, if they exist)

.. code-block:: shell

    toolbox/entitlement/undeploy.sh

Testing and Waiting
===================

* Test a PEM key in a local ``podman`` container (requires access to
  ``registry.access.redhat.com/ubi8/ubi``)

.. code-block:: shell

   toolbox/entitlement/test_in_podman.sh /path/to/key.pem

* Test a PEM key inside a cluster Pod (without deploying it)


.. code-block:: shell

   toolbox/entitlement/test_in_cluster.sh /path/to/key.pem

* Test cluster-wide entitlement

(currently tested on a *random* node of the cluster)

.. code-block:: shell

    toolbox/entitlement/test_cluster.sh [--no-inspect]

* Wait for the cluster-wide entitlement to be deployed

(currently tested on a *random* node of the cluster)

.. code-block:: shell

    toolbox/entitlement/wait.sh

Troubleshooting
===============

.. code-block:: shell

    toolbox/entitlement/inspect.sh
