import os
import sys
import logging

from projects.core.library.ansible_toolbox import (
    RunAnsibleRole, AnsibleRole,
    AnsibleMappedParams, AnsibleConstant,
    AnsibleSkipConfigGeneration
)

class Server:
    """
    Commands relating to the deployment of servers on OpenShift
    """

    @AnsibleRole("server_deploy_opensearch")
    @AnsibleMappedParams
    def deploy_opensearch(self,
                          secret_properties_file,
                          namespace="opensearch",
                          name="opensearch",

                    ):
        """
        Deploy OpenSearch and OpenSearch-Dashboards

        Example of secret properties file:

        user_password=passwd
        admin_password=adminpasswd

        Args:
          namespace: namespace in which the application will be deployed
          name: name to give to the opensearch instance
          secret_properties_file: Path of a file containing the properties of LDAP secrets.
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("server_deploy_nginx_server")
    @AnsibleMappedParams
    def deploy_nginx_server(self, namespace, directory):
        """
        Deploy an NGINX HTTP server

        Args:
            namespace: namespace where the server will be deployed. Will be create if it doesn't exist.
            directory: directory containing the files to serve on the HTTP server.
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("server_deploy_redis_server")
    @AnsibleMappedParams
    def deploy_redis_server(self, namespace):
        """
        Deploy a redis server

        Args:
            namespace: namespace where the server will be deployed. Will be create if it doesn't exist.
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("server_deploy_ldap")
    @AnsibleConstant("Name of the admin user",
                     "admin_user", "admin")
    @AnsibleMappedParams
    def deploy_ldap(self,
                    idp_name, username_prefix, username_count: int, secret_properties_file,
                    use_ocm=False, use_rosa=False,
                    cluster_name=None,
                    wait=False):
        """
        Deploy OpenLDAP and LDAP Oauth

        Example of secret properties file:

        admin_password=adminpasswd

        Args:
          idp_name: Name of the LDAP identity provider.
          username_prefix: Prefix for the creation of the users (suffix is 0..username_count)
          username_count: Number of users to create.
          secret_properties_file: Path of a file containing the properties of LDAP secrets.
          use_ocm: If true, use `ocm create idp` to deploy the LDAP identity provider.
          use_rosa: If true, use `rosa create idp` to deploy the LDAP identity provider.
          cluster_name: Cluster to use when using OCM or ROSA.
          wait: If True, waits for the first user (0) to be able to login into the cluster.
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("server_undeploy_ldap")
    @AnsibleMappedParams
    def undeploy_ldap(self, idp_name,
                      use_ocm=False, use_rosa=False,
                      cluster_name=None,
                      ):
        """
        Undeploy OpenLDAP and LDAP Oauth

        Args:
          idp_name: Name of the LDAP identity provider.
          use_ocm: If true, use `ocm delete idp` to delete the LDAP identity provider.
          use_rosa: If true, use `rosa delete idp` to delete the LDAP identity provider.
          cluster_name: Cluster to use when using OCM or ROSA.
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("server_deploy_minio_s3_server")
    @AnsibleConstant("Name of the user/access key to use to connect to the Minio server",
                     "access_key", "minio")
    @AnsibleConstant("Name of the Minio admin user",
                     "root_user", "admin")
    @AnsibleMappedParams
    def deploy_minio_s3_server(self, secret_properties_file, namespace="minio", bucket_name="myBucket"):
        """
        Deploy Minio S3 server

        Example of secret properties file:

        user_password=passwd
        admin_password=adminpasswd

        Args:
            secret_properties_file: Path of a file containing the properties of S3 secrets.
            namespace: Namespace in which Minio should be deployed.
            bucket_name: The name of the default bucket to create in Minio.
        """

        return RunAnsibleRole(locals())
