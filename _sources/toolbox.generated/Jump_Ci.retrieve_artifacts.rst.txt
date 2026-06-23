:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Jump_Ci.retrieve_artifacts


jump_ci retrieve_artifacts
==========================

Prepares the jump host for running a CI test step:




Parameters
----------


``cluster``  

* Name of the cluster lock to use


``lock_owner``  

* Name of the lock owner


``remote_dir``  

* Name of remote directory to retrieve.


``local_dir``  

* Name of the local dir where to store the results, within the extra logs artifacts directory.

* default value: ``artifacts``


``skip_cluster_lock``  

* If True, skip the cluster is lock check (eg, when included from another role).

