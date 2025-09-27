:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Cluster.create_htpasswd_adminuser


cluster create_htpasswd_adminuser
=================================

Create an htpasswd admin user.

Will remove any other existing OAuth.

Example of password file:
password=my-strong-password


Parameters
----------


``username``  

* Username of the htpasswd user.


``passwordfile``  

* Password file where the user's password is stored. Will be sourced.


``wait``  

* If True, waits for the user to be able to login into the cluster.


# Constants
# Name of the secret that will contain the htpasswd passwords
# Defined as a constant in Cluster.create_htpasswd_adminuser
cluster_create_htpasswd_user_secret_name: htpasswd-secret

# Name of the htpasswd IDP being created
# Defined as a constant in Cluster.create_htpasswd_adminuser
cluster_create_htpasswd_user_htpasswd_idp_name: htpasswd

# Role that will be given to the user group
# Defined as a constant in Cluster.create_htpasswd_adminuser
cluster_create_htpasswd_user_role: cluster-admin

# Name of the group that will be created for the user
# Defined as a constant in Cluster.create_htpasswd_adminuser
cluster_create_htpasswd_user_groupname: local-admins
