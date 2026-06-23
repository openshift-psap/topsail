:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Server.deploy_ldap


server deploy_ldap
==================

Deploy OpenLDAP and LDAP Oauth

Example of secret properties file:

admin_password=adminpasswd


Parameters
----------


``idp_name``  

* Name of the LDAP identity provider.


``username_prefix``  

* Prefix for the creation of the users (suffix is 0..username_count)


``username_count``  

* Number of users to create.
* type: Int


``secret_properties_file``  

* Path of a file containing the properties of LDAP secrets.


``use_ocm``  

* If true, use `ocm create idp` to deploy the LDAP identity provider.


``use_rosa``  

* If true, use `rosa create idp` to deploy the LDAP identity provider.


``cluster_name``  

* Cluster to use when using OCM or ROSA.


``wait``  

* If True, waits for the first user (0) to be able to login into the cluster.


# Constants
# Name of the admin user
# Defined as a constant in Server.deploy_ldap
server_deploy_ldap_admin_user: admin
