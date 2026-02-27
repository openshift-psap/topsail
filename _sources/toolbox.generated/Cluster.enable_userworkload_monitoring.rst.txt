:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Cluster.enable_userworkload_monitoring


cluster enable_userworkload_monitoring
======================================

Enables user workload monitoring for OpenShift

Creates the necessary ConfigMaps to enable user workload monitoring
and labels the specified namespaces for monitoring.


Parameters
----------


``namespaces``  

* List of namespaces to enable monitoring for. Each namespace will get the openshift.io/user-monitoring=true label.
* type: List

