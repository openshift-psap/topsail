:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Busy_Cluster.create_configmaps


busy_cluster create_configmaps
==============================

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

* Prefix to give to the configmaps/secrets to create

* default value: ``busy``


``count``  

* Number of configmaps/secrets to create

* default value: ``10``


``labels``  

* Dict of the key/value labels to set for the configmap/secrets


``as_secrets``  

* If True, creates secrets instead of configmaps


``entries``  

* Number of entries to create

* default value: ``10``


``entry_values_length``  

* Length of an entry value

* default value: ``1024``


``entry_keys_prefix``  

* The prefix to use to create the entry values

* default value: ``entry-``

