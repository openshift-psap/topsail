:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Cluster.deploy_minio_s3_server


cluster deploy_minio_s3_server
==============================

Deploy Minio S3 server

Example of secret properties file:

user_password=passwd
admin_password=adminpasswd


Parameters
----------


``secret_properties_file``  

* Path of a file containing the properties of S3 secrets.


``namespace``  

* Namespace in which Minio should be deployed.

* default value: ``minio``


``bucket_name``  

* The name of the default bucket to create in Minio.

* default value: ``myBucket``


# Constants
# Name of the Minio admin user
# Defined as a constant in Cluster.deploy_minio_s3_server
cluster_deploy_minio_s3_server_root_user: admin

# Name of the user/access key to use to connect to the Minio server
# Defined as a constant in Cluster.deploy_minio_s3_server
cluster_deploy_minio_s3_server_access_key: minio
