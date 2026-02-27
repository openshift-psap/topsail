:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Cluster.fill_workernodes


cluster fill_workernodes
========================

Fills the worker nodes with place-holder Pods with the maximum available amount of a given resource name.




Parameters
----------


``namespace``  

* Namespace in which the place-holder Pods should be deployed

* default value: ``default``


``name``  

* Name prefix to use for the place-holder Pods

* default value: ``resource-placeholder``


``label_selector``  

* Label to use to select the nodes to fill

* default value: ``node-role.kubernetes.io/worker``

