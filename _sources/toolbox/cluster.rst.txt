=======
Cluster
=======

.. _toolbox_cluster_scale:

Cluster Scale
=============

* Set number of nodes with given instance type

.. code-block:: shell

    ./run_toolbox.py cluster set_scale <machine-type> <replicas> [--base_machineset=BASE_MACHINESET]

**Example usage:**

.. code-block:: shell

    # Set the total number of g4dn.xlarge nodes to 2
    ./run_toolbox.py cluster set_scale g4dn.xlarge 2

.. code-block:: shell

    # Set the total number of g4dn.xlarge nodes to 5,
    # even when there are some machinesets that might need to be downscaled
    # to 0 to achive that.
    ./run_toolbox.py cluster set_scale g4dn.xlarge 5 --force

 .. code-block:: shell

    # list the machinesets of the cluster
    $ oc get machinesets -n openshift-machine-api

    NAME                                      DESIRED   CURRENT   READY   AVAILABLE   AGE
    playground-8p9vm-worker-eu-central-1a      1         1         1       1           57m
    playground-8p9vm-worker-eu-central-1b      1         1         1       1           57m
    playground-8p9vm-worker-eu-central-1c      0         0                             57m

    # Set the total number of m5.xlarge nodes to 1
    # using 'playground-8p9vm-worker-eu-central-1c' to derive the new machineset
    ./run_toolbox.py cluster set_scale m5.xlarge 1 --base_machineset=playground-8p9vm-worker-eu-central-1c
