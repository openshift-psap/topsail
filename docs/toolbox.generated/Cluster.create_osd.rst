:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Cluster.create_osd


cluster create_osd
==================

Create an OpenShift Dedicated cluster.

Secret_file:
  KUBEADMIN_PASS: password of the default kubeadmin user.
  AWS_ACCOUNT_ID
  AWS_ACCESS_KEY
  AWS_SECRET_KEY: Credentials to access AWS.


Parameters
----------


``cluster_name``  

* The name to give to the cluster.


``secret_file``  

* The file containing the cluster creation credentials.


``kubeconfig``  

* The KUBECONFIG file to populate with the access to the cluster.


``version``  

* OpenShift version to deploy.

* default value: ``4.10.15``


``region``  

* AWS region where the cluster will be deployed.

* default value: ``us-east-1``


``htaccess_idp_name``  

* Name of the Identity provider that will be created for the admin account.

* default value: ``htpasswd``


``compute_machine_type``  

* Name of the AWS machine instance type that will be used for the compute nodes.

* default value: ``m5.xlarge``


``compute_nodes``  

* The number of compute nodes to create. A minimum of 2 is required by OSD.
* type: Int

* default value: ``2``


# Constants
# Name of the worker node machinepool
# Defined as a constant in Cluster.create_osd
cluster_create_osd_machinepool_name: default

# Group that the admin account will be part of.
# Defined as a constant in Cluster.create_osd
cluster_create_osd_kubeadmin_group: cluster-admins

# Name of the admin account that will be created.
# Defined as a constant in Cluster.create_osd
cluster_create_osd_kubeadmin_name: kubeadmin
