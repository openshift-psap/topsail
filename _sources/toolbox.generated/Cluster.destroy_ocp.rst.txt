:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Cluster.destroy_ocp


cluster destroy_ocp
===================

Destroy an OpenShift cluster




Parameters
----------


``region``  

* The AWS region where the cluster lives. If empty and --confirm is passed, look up from the cluster.


``tag``  

* The resource tag key. If empty and --confirm is passed, look up from the cluster.


``confirm``  

* If the region/label are not set, and --confirm is passed, destroy the current cluster.


``tag_value``  

* The resource tag value.

* default value: ``owned``


``openshift_install``  

* The path to the `openshift-install` to use to destroy the cluster. If empty, pick it up from the `deploy-cluster` subproject.

* default value: ``openshift-install``

