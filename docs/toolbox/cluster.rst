=======
Cluster
=======

.. _toolbox_cluster_scale:

Cluster Scale
=============

* Set number of nodes with given instance type

.. code-block:: shell

    ./run_toolbox.py cluster set_scale <machine-type> <replicas>

**Example usage:**

.. code-block:: shell

    # Set the total number of g4dn.xlarge nodes to 2
    ./run_toolbox.py cluster set_scale g4dn.xlarge 2

.. code-block:: shell

    # Set the total number of g4dn.xlarge nodes to 5,
    # even when there are some machinesets that might need to be downscaled
    # to 0 to achive that.
    ./run_toolbox.py cluster set_scale g4dn.xlarge 5 --force
