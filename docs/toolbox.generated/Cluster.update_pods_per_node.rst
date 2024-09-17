:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Cluster.update_pods_per_node


cluster update_pods_per_node
============================

Update the maximum number of Pods per Nodes, and Pods per Core See alse: https://docs.openshift.com/container-platform/4.14/nodes/nodes/nodes-nodes-managing-max-pods.html




Parameters
----------


``max_pods``  

* The maximum number of Pods per nodes

* default value: ``250``


``pods_per_core``  

* The maximum number of Pods per core

* default value: ``10``


``name``  

* The name to give to the KubeletConfig object

* default value: ``set-max-pods``


``label``  

* The label selector for the nodes to update

* default value: ``pools.operator.machineconfiguration.openshift.io/worker``


``label_value``  

* The expected value for the label selector

