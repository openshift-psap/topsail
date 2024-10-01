:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Cluster.deploy_opensearch


cluster deploy_opensearch
=========================

Deploy OpenSearch and OpenSearch-Dashboards

Example of secret properties file:

user_password=passwd
admin_password=adminpasswd


Parameters
----------


``secret_properties_file``  

* Path of a file containing the properties of LDAP secrets.


``namespace``  

* Namespace in which the application will be deployed

* default value: ``opensearch``


``name``  

* Name to give to the opensearch instance

* default value: ``opensearch``

