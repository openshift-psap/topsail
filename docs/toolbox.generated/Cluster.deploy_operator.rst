:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Cluster.deploy_operator


cluster deploy_operator
=======================

Deploy an operator from OperatorHub catalog entry.




Parameters
----------


``catalog``  

* Name of the catalog containing the operator.


``manifest_name``  

* Name of the operator package manifest.


``namespace``  

* Namespace in which the operator will be deployed, or 'all' to deploy in all the namespaces.


``version``  

* Version to deploy. If unspecified, deploys the latest version available in the selected channel.


``channel``  

* Channel to deploy from. If unspecified, deploys the CSV's default channel. Use '?' to list the available channels for the given package manifest.


``installplan_approval``  

* InstallPlan approval mode (Automatic or Manual).

* default value: ``Manual``


``catalog_namespace``  

* Namespace in which the CatalogSource will be deployed

* default value: ``openshift-marketplace``


``deploy_cr``  

* If set, deploy the first example CR found in the CSV.
* type: Bool


``namespace_monitoring``  

* If set, enable OpenShift namespace monitoring.
* type: Bool


``all_namespaces``  

* If set, deploy the CSV in all the namespaces.
* type: Bool


``config_env_names``  

* If not empty, a list of config env names to pass to the subscription
* type: List


``csv_base_name``  

* If not empty, base name of the CSV. If empty, use the manifest_name.

