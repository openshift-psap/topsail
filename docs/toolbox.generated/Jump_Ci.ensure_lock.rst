:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Jump_Ci.ensure_lock


jump_ci ensure_lock
===================

Ensure that cluster lock with a given name is taken. Fails otherwise.




Parameters
----------


``cluster``  

* Name of the cluster lock to test


``owner``  

* Name of the lock owner


``check_kubeconfig``  

* If enabled, ensure that the cluster's kubeconfig file exists

* default value: ``True``

