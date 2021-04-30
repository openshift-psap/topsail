===========
Entitlement
===========


Deployment
==========

* Deploy the entitlement cluster-wide

Deploy a PEM key and RHSM configuration

.. code-block:: shell

    toolbox/entitlement/deploy.sh --pem /path/to/key.pem

* Undeploy the cluster-wide entitlement

.. code-block:: shell

    toolbox/entitlement/undeploy.sh

Testing and Waiting
===================

* Test cluster-wide entitlement

(currently tested on a *random* node of the cluster)

.. code-block:: shell

    toolbox/entitlement/test.sh [--no-inspect]

* Wait for the cluster-wide entitlement to be deployed

(currently tested on a *random* node of the cluster)

.. code-block:: shell

    toolbox/entitlement/wait.sh

Troubleshooting
===============

.. code-block:: shell

    toolbox/entitlement/inspect.sh
