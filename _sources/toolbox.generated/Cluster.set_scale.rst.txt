:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Cluster.set_scale


cluster set_scale
=================

Ensures that the cluster has exactly ``scale`` nodes with instance_type ``instance_type``

If the machinesets of the given instance type already have the required total number of replicas,
their replica parameters will not be modified.
Otherwise,
- If there's only one machineset with the given instance type, its replicas will be set to the value of this parameter.
- If there are other machinesets with non-zero replicas, the playbook will fail, unless the `force` parameter is
set to true. In that case, the number of replicas of the other machinesets will be zeroed before setting the replicas
of the first machineset to the value of this parameter."
- If `--base-machineset=machineset` flag is passed, `machineset` machineset will be used to derive the new
machinetset (otherwise, the first machinetset of the listing will be used). This is useful if the desired `instance_type`
is only available in some specific regions and, controlled by different machinesets.

Example: ./run_toolbox.py cluster set_scale g4dn.xlarge 1 # ensure that the cluster has 1 GPU node


Parameters
----------


``instance_type``  

* The instance type to use, for example, g4dn.xlarge


``scale``  

* The number of required nodes with given instance type


``base_machineset``  

* Name of a machineset to use to derive the new one. Default: pickup the first machineset found in `oc get machinesets -n openshift-machine-api`.


``force``  

* Missing documentation for force


``taint``  

* Taint to apply to the machineset.


``name``  

* Name to give to the new machineset.


``spot``  

* Set to true to request spot instances from AWS. Set to false (default) to request on-demand instances.


``disk_size``  

* Size of the EBS volume to request for the root partition

