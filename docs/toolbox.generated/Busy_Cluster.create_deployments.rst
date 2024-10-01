:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Busy_Cluster.create_deployments


busy_cluster create_deployments
===============================

Creates configmaps and secrets to make a cluster busy




Parameters
----------


``namespace_label_key``  

* The label key to use to locate the namespaces to populate

* default value: ``busy-cluster.topsail``


``namespace_label_value``  

* The label value to use to locate the namespaces to populate

* default value: ``yes``


``prefix``  

* Prefix to give to the deployments to create

* default value: ``busy``


``count``  

* Number of deployments to create

* default value: ``1``


``labels``  

* Dict of the key/value labels to set for the deployments


``replicas``  

* Number of replicas to set for the deployments

* default value: ``1``


``services``  

* Number of services to create for each of the deployments

* default value: ``1``


``image_pull_back_off``  

* If True, makes the containers image pull fail.


``crash_loop_back_off``  

* If True, makes the containers fail. If a integer value, wait this many seconds before failing.

