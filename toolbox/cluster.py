import sys, os

from toolbox._common import RunAnsibleRole, AnsibleRole


class Cluster:
    """
    Commands relating to cluster scaling, upgrading and environment capture
    """
    @staticmethod
    @AnsibleRole("cluster_set_scale")
    def set_scale(instance_type, scale, base_machineset="", force=False, taint="", name=""):
        """
        Ensures that the cluster has exactly `scale` nodes with instance_type `instance_type`

        If the machinesets of the given instance type already have the required total number of replicas,
        their replica parameters will not be modified.
        Otherwise,
        - If there's only one machineset with the given instance type, its replicas will be set to the value of this parameter.

        - If there are other machinesets with non-zero replicas, the playbook will fail, unless the 'force_scale' parameter is
        set to true. In that case, the number of replicas of the other machinesets will be zeroed before setting the replicas
        of the first machineset to the value of this parameter."

        - If `--base-machineset=machineset` flag is passed, `machineset` machineset will be used to derive the new
        machinetset (otherwise, the first machinetset of the listing will be used). This is useful if the desired `instance_type`
        is only available in some specific regions and, controlled by different machinesets.

        Example: ./run_toolbox.py cluster set_scale g4dn.xlarge 1 # ensure that the cluster has 1 GPU node

        Args:
            instance_type: The instance type to use, for example, g4dn.xlarge
            scale: The number of required nodes with given instance type
            base_machineset: Name of a machineset to use to derive the new one. Default: pickup the first machineset found in `oc get machinesets -n openshift-machine-api`.
            taint: Taint to apply to the machineset.
            name: Name to give to the new machineset.
        """
        opts = {
            "machineset_instance_type": instance_type,
            "scale": scale,
            "machineset_taint": taint,
            "machineset_name": name,
            "cluster_ensure_machineset_base_machineset": base_machineset,
            "force_scale": force,
        }

        return RunAnsibleRole(opts)

    @staticmethod
    @AnsibleRole("cluster_upgrade_to_image")
    def upgrade_to_image(image):
        """
        Upgrades the cluster to the given image

        Args:
            image: The image to upgrade the cluster to
        """
        return RunAnsibleRole({"cluster_upgrade_image": image})

    @staticmethod
    @AnsibleRole("cluster_capture_environment")
    def capture_environment():
        """
        Captures the cluster environment

        Args:
            image: The image to upgrade the cluster to
        """
        return RunAnsibleRole()


    @staticmethod
    @AnsibleRole("cluster_deploy_operator")
    def deploy_operator(catalog, manifest_name, namespace, version=None, channel=None, install_plan="Manual", deploy_cr=False, ns_monitoring=False):
        """
        Deploy an operator from OperatorHub catalog entry.

        Args:
            catalog: Name of the catalog containing the operator.
            manifest_name: Name of the operator package manifest.
            namespace: Namespace in which the operator will be deployed, or 'all' to deploy in all the namespaces.
            channel: Optional channel to deploy from. If unspecified, deploys the CSV's default channel. Use '?' to list the available channels for the given package manifest.
            version: Optional version to deploy. If unspecified, deploys the latest version available in the selected channel.
            install_plan: Optional InstallPlan approval mode (Automatic or Manual). Default: Manual.
            deploy_cr: Optional boolean flag to deploy the first example CR found in the CSV.
            ns_monitoring: Optional boolean flag to enable OpenShift namespace monitoring. Default: False.
        """

        opts = {
            "cluster_deploy_operator_catalog": catalog,
            "cluster_deploy_operator_manifest_name": manifest_name,
        }


        if namespace == "all":
            opts["cluster_deploy_operator_all_namespaces"] = "True"
            opts["cluster_deploy_operator_namespace"] = "openshift-operators"
            if ns_monitoring:
                print("Namespace monitoring cannot be enabled when deploying in all the namespaces.")
                sys.exit(1)

            print(f"Deploying the operator in all the namespaces.")
        else:
            opts["cluster_deploy_operator_namespace"] = namespace
            opts["cluster_deploy_operator_namespace_monitoring"] = ns_monitoring
            if ns_monitoring:
                print(f"Enabling namespace monitoring.")

            print(f"Deploying the operator using namespace '{namespace}'.")


        if channel is not None:
            opts["cluster_deploy_operator_channel"] = channel
            print(f"Deploying the operator using channel '{channel}'.")

        if version is not None:
            if channel is None:
                print("Version may only be specified if --channel is specified")
                sys.exit(1)

            opts["cluster_deploy_operator_version"] = version
            print(f"Deploying the operator using version '{version}'.")

        opts["cluster_deploy_operator_installplan_approval"] = install_plan
        if install_plan not in ("Manual", "Automatic"):
            print(f"--install-plan can only be Manual or Automatic. Received '{install_plan}'.")
            sys.exit(1)

        print(f"Deploying the operator using InstallPlan approval mode '{install_plan}'.")

        opts["cluster_deploy_operator_deploy_cr"] = deploy_cr
        if deploy_cr:
            print(f"Deploying the operator default CR.")


        print("Deploying the operator.")

        return RunAnsibleRole(opts)

    @staticmethod
    @AnsibleRole("cluster_deploy_aws_efs")
    def deploy_aws_efs():
        """
        Deploy AWS EFS CSI driver and configure AWS accordingly.

        Assumes that AWS (credentials, Ansible module, Python module) is properly configured in the system.
        """
        return RunAnsibleRole({})

    @staticmethod
    @AnsibleRole("cluster_deploy_minio_s3_server")
    def deploy_minio_s3_server(secret_properties_file):
        """
        Deploy Minio S3 server

        Example of secret properties file:

        user_password=passwd
        admin_password=adminpasswd

        Args:
            secret_properties_file: Path of a file containing the properties of S3 secrets.
        """

        opts = {
            "cluster_deploy_minio_s3_server_secret_properties": secret_properties_file,
        }

        return RunAnsibleRole(opts)

    @staticmethod
    @AnsibleRole("cluster_deploy_nginx_server")
    def deploy_nginx_server(namespace, directory):
        """
        Deploy an NGINX HTTP server

        Args:
            namespace: namespace where the server will be deployed. Will be create if it doesn't exist.
            directory: directory containing the files to serve on the HTTP server.
        """

        opts = {
            "cluster_deploy_nginx_server_namespace": namespace,
            "cluster_deploy_nginx_server_directory": directory,
        }

        return RunAnsibleRole(opts)

    @staticmethod
    @AnsibleRole("cluster_deploy_redis_server")
    def deploy_redis_server(namespace):
        """
        Deploy a redis server

        Args:
            namespace: namespace where the server will be deployed. Will be create if it doesn't exist.
        """

        opts = {
            "cluster_deploy_redis_server_namespace": namespace,
        }

        return RunAnsibleRole(opts)

    @staticmethod
    @AnsibleRole("cluster_prometheus_db")
    def reset_prometheus_db(label="app.kubernetes.io/component=prometheus", namespace="openshift-monitoring"):
        """
        Resets Prometheus database, by destroying its Pod

        By default, target OpenShift Prometheus Pod.

        Args:
          label: Optional. Label to use to identify Prometheus Pod.
          namespace: Optional. Namespace where to search Promtheus Pod.
        """

        opts = {
            "cluster_prometheus_db_mode": "reset",
            "cluster_prometheus_db_label": label,
            "cluster_prometheus_db_namespace": namespace,
        }

        return RunAnsibleRole(opts)

    @staticmethod
    @AnsibleRole("cluster_prometheus_db")
    def dump_prometheus_db(label="app.kubernetes.io/component=prometheus", namespace="openshift-monitoring", name_prefix="prometheus"):
        """
        Dump Prometheus database into a file

        By default, target OpenShift Prometheus Pod.

        Args:
          label: Optional. Label to use to identify Prometheus Pod.
          namespace: Optional. Namespace where to search Promtheus Pod.
          name_prefix: Optional. Name prefix for the archive that will be stored.
        """

        opts = {
            "cluster_prometheus_db_mode": "dump",
            "cluster_prometheus_db_label": label,
            "cluster_prometheus_db_namespace": namespace,
            "cluster_prometheus_db_dump_name_prefix": name_prefix,
        }

        return RunAnsibleRole(opts)

    @staticmethod
    @AnsibleRole("cluster_destroy_ocp")
    def destroy_ocp(region="", tag="", confirm=False, tag_value="owned", openshift_install="openshift-install"):
        """
        Destroy an OpenShift cluster

        Args:
          region: Optional. The AWS region where the cluster lives. If empty and --confirm is passed, look up from the cluster.
          label: Optional. The resource tag key. If empty and --confirm is passed, look up from the cluster.
          confirm: If the region/label are not set, and --confirm is passed, destroy the current cluster.
          tag_value: Optional. The resource tag value. Default: 'owned'.
          openshift_install: Optional. The path to the `openshift-install` to use to destroy the cluster. If empty, pick it up from the `deploy-cluster` subproject. Default: 'openshift-installer'
        """


        opt = {
            "cluster_destroy_ocp_region": region,
            "cluster_destroy_ocp_tag": tag,
            "cluster_destroy_ocp_confirm": confirm,
            "cluster_destroy_ocp_tag_value": tag_value,
            "cluster_destroy_ocp_openshift_install": openshift_install,
        }

        return RunAnsibleRole(opt)

    @staticmethod
    @AnsibleRole("cluster_create_osd")
    def create_osd(cluster_name, secret_file, kubeconfig,
                   version="4.10.15",
                   region="us-east-1",
                   kubeadmin_name="kubeadmin",
                   kubeadmin_group="cluster-admins",
                   htaccess_idp_name="htpasswd",
                   compute_machine_type="m5.xlarge",
                   compute_nodes : int = 2,
                   ):
        """
        Create an OpenShift Dedicated cluster.

        Secret_file:
          KUBEADMIN_PASS: password of the default kubeadmin user.
          AWS_ACCOUNT_ID
          AWS_ACCESS_KEY
          AWS_SECRET_KEY: Credentials to access AWS.

        Args:
          cluster_name: The name to give to the cluster.
          secret_file: The file containing the cluster creation credentials.
          kubeconfig: The KUBECONFIG file to populate with the access to the cluster.
          compute_nodes: The number of compute nodes to create. A minimum of 2 is required by OSD.
        """

        opts = dict(
            cluster_create_osd_cluster_name=cluster_name,
            cluster_create_osd_secret_file=secret_file,
            cluster_create_osd_version=version,
            cluster_create_osd_region=region,
            cluster_create_osd_kubeconfig=kubeconfig,
            cluster_create_osd_kubeadmin_name=kubeadmin_name,
            cluster_create_osd_kubeadmin_group=kubeadmin_group,
            cluster_create_osd_htaccess_idp_name=htaccess_idp_name,
            cluster_create_osd_compute_machine_type=compute_machine_type,
            cluster_create_osd_compute_nodes=compute_nodes,
        )

        return RunAnsibleRole(opts)

    @staticmethod
    @AnsibleRole("cluster_destroy_osd")
    def destroy_osd(cluster_name):
        """
        Destroy an OpenShift Dedicated cluster.

        Args:
          cluster_name: The name of the cluster to destroy.
        """

        opts = dict(
            cluster_destroy_osd_cluster_name=cluster_name,
        )

        return RunAnsibleRole(opts)

    @staticmethod
    @AnsibleRole("cluster_deploy_ldap")
    def deploy_ldap(self,
                    idp_name, username_prefix, username_count: int, secret_properties_file,
                    use_ocm=False, use_rosa=False,
                    cluster_name=None,
                    wait=False):
        """
        Deploy OpenLDAP and LDAP Oauth

        Example of secret properties file:

        user_password=passwd
        admin_password=adminpasswd

        Args:
          idp_name: Name of the LDAP identity provider.
          username_prefix: Prefix for the creation of the users (suffix is 0..username_count)
          username_count: Number of users to create.
          secret_properties_file: Path of a file containing the properties of LDAP secrets.
          use_ocm: Optional. If true, use `ocm create idp` to deploy the LDAP identity provider.
          use_rosa: Optional. If true, use `rosa create idp` to deploy the LDAP identity provider.
          cluster_name: Optional. Cluster to use when using OCM or ROSA.
          wait: Optional. If True, waits for the first user (0) to be able to login into the cluster.
        """

        opts = {
            "cluster_deploy_ldap_idp_name": idp_name,
            "cluster_deploy_ldap_username_prefix": username_prefix,
            "cluster_deploy_ldap_username_count": username_count,
            "cluster_deploy_ldap_secret_properties": secret_properties_file,
            "cluster_deploy_ldap_use_ocm": use_ocm,
            "cluster_deploy_ldap_use_rosa": use_rosa,
            "cluster_deploy_ldap_cluster_name": cluster_name,
            "cluster_deploy_ldap_wait": wait,
        }

        return RunAnsibleRole(opts)

    @staticmethod
    @AnsibleRole("cluster_undeploy_ldap")
    def undeploy_ldap(self, idp_name,
                      use_ocm=False, use_rosa=False,
                      cluster_name=None,
                      ):
        """
        Undeploy OpenLDAP and LDAP Oauth

        Args:
          idp_name: Name of the LDAP identity provider.
          use_ocm: Optional. If true, use `ocm delete idp` to delete the LDAP identity provider.
          use_rosa: Optional. If true, use `rosa delete idp` to delete the LDAP identity provider.
          cluster_name: Optional. Cluster to use when using OCM or ROSA.
        """

        opts = {
            "cluster_undeploy_ldap_idp_name": idp_name,
            "cluster_undeploy_ldap_use_ocm": use_ocm,
            "cluster_undeploy_ldap_use_rosa": use_rosa,
            "cluster_deploy_ldap_cluster_name": cluster_name,
        }

        return RunAnsibleRole(opts)

    @staticmethod
    @AnsibleRole("cluster_preload_image")
    def preload_image(name, image, namespace="default",
                      node_selector_key="", node_selector_value="",
                      pod_toleration_key="", pod_toleration_effect=""):
        """
        Preload a container image on all the nodes of a cluster.

        Args:
          name: Name to give to the DaemonSet used for preloading the image.
          image: Container image to preload on the nodes.
          namespace: Optional. Namespace in which the DaemonSet will be created.
          node_selector_key: Optional. NodeSelector key to apply to the DaemonSet.
          node_selector_value: Optional. NodeSelector value to apply to the DaemonSet.
          pod_toleration_key: Optional. Pod toleration to apply to the DaemonSet.
          pod_toleration_effect: Optional. Pod toleration to apply to the DaemonSet.
        """

        toolbox_name_suffix = os.environ.get("ARTIFACT_TOOLBOX_NAME_SUFFIX", "")
        # use `name` as first suffix in the directory name
        os.environ["ARTIFACT_TOOLBOX_NAME_SUFFIX"] = f"_{name}{toolbox_name_suffix}"

        opts = {
            "cluster_preload_image_ds_name": name,
            "cluster_preload_image_ds_namespace": namespace,
            "cluster_preload_image_ds_image": image,
            "cluster_preload_image_node_selector_key": node_selector_key,
            "cluster_preload_image_node_selector_value": node_selector_value,
            "cluster_preload_image_pod_toleration_key": pod_toleration_key,
            "cluster_preload_image_pod_toleration_effect": pod_toleration_effect,
        }

        return RunAnsibleRole(opts)

    @staticmethod
    @AnsibleRole("cluster_create_htpasswd_user")
    def create_htpasswd_adminuser(username, passwordfile, wait=False):
        """
        Create an htpasswd admin user.

        Will remove any other existing OAuth.

        Example of password file:
        password=my-strong-password

        Args:
          username: Username of the htpasswd user.
          passwordfile: Password file where the user's password is stored. Will be sourced.
          wait: Optional. If True, waits for the user to be able to login into the cluster.
        """

        opts = {
            "cluster_create_htpasswd_user_username": username,
            "cluster_create_htpasswd_user_passwordfile": passwordfile,
            "cluster_create_htpasswd_user_groupname": "local-admins",
            "cluster_create_htpasswd_user_role": "cluster-admin",
            "cluster_create_htpasswd_user_groupname": "local-admins",
            "cluster_create_htpasswd_user_wait": wait,

        }

        return RunAnsibleRole(opts)
