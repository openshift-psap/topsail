:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Cpt.deploy_cpt_dashboard


cpt deploy_cpt_dashboard
========================

Deploy and configure the CPT Dashboard

Example of secret properties file:

admin_password=adminpasswd


Parameters
----------


``frontend_istag``  

* Imagestream tag to use for the frontend container


``backend_istag``  

* Imagestream tag to use for the backend container


``plugin_name``  

* Name of the CPT Dashboard plugin to configure


``es_url``  

* URL of the OpenSearch backend


``es_indice``  

* Indice of the OpenSearch backend


``es_username``  

* Username to use to login into OpenSearch


``secret_properties_file``  

* Path of a file containing the OpenSearch user credentials


``namespace``  

* Namespace in which the application will be deployed

* default value: ``topsail-cpt-dashboard``

