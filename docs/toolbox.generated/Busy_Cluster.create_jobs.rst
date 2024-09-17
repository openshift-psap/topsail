:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Busy_Cluster.create_jobs


busy_cluster create_jobs
========================

Creates jobs to make a cluster busy




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

* default value: ``10``


``labels``  

* Dict of the key/value labels to set for the deployments


``replicas``  

* The number of parallel tasks to execute

* default value: ``2``


``runtime``  

* The runtime of the Job Pods in seconds, of inf

* default value: ``120``

