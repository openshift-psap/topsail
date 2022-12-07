import sys, os

from toolbox._common import RunAnsibleRole, AnsibleRole, AnsibleMappedParams, AnsibleConstant, AnsibleSkipConfigGeneration


class Cluster:
    """
    Commands relating to cluster scaling, upgrading and environment capture
    """

    @AnsibleRole("cluster_set_scale")
    def set_scale(self, instance_type, scale, base_machineset="", force=False, taint="", name=""):
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

    @AnsibleRole("cluster_upgrade_to_image")
    @AnsibleMappedParams
    def upgrade_to_image(self, image):
        """
        Upgrades the cluster to the given image

        Args:
            image: The image to upgrade the cluster to
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("cluster_capture_environment")
    @AnsibleMappedParams
    def capture_environment(self):
        """
        Captures the cluster environment

        Args:
            image: The image to upgrade the cluster to
        """

        return RunAnsibleRole()


    @AnsibleRole("cluster_deploy_operator")
    @AnsibleMappedParams
    def deploy_operator(self, catalog, manifest_name, namespace,
                        version='', channel='',
                        installplan_approval="Manual",
                        deploy_cr: bool = False,
                        namespace_monitoring: bool = False,
                        all_namespaces: bool = False):
        """
        Deploy an operator from OperatorHub catalog entry.

        Args:
            catalog: Name of the catalog containing the operator.
            manifest_name: Name of the operator package manifest.
            namespace: Namespace in which the operator will be deployed, or 'all' to deploy in all the namespaces.
            channel: Channel to deploy from. If unspecified, deploys the CSV's default channel. Use '?' to list the available channels for the given package manifest.
            version: Version to deploy. If unspecified, deploys the latest version available in the selected channel.
            installplan_approval: InstallPlan approval mode (Automatic or Manual).
            deploy_cr: If set, deploy the first example CR found in the CSV.
            namespace_monitoring: If set, enable OpenShift namespace monitoring.
            all_namespaces: If set, deploy the CSV in all the namespaces.
        """

        if namespace == "all":
            all_namespaces = True
            namespace = "openshift-operators"

            if namespace_monitoring:
                print("Namespace monitoring cannot be enabled when deploying in all the namespaces.")
                sys.exit(1)

            print(f"Deploying the operator in all the namespaces.")


        if namespace_monitoring:
            print(f"Enabling namespace monitoring.")

        print(f"Deploying the operator using namespace '{namespace}'.")

        if channel:
            print(f"Deploying the operator using channel '{channel}'.")

        if version:
            if channel:
                print("Version may only be specified if --channel is specified")
                sys.exit(1)

            print(f"Deploying the operator using version '{version}'.")

        if installplan not in ("Manual", "Automatic"):
            print(f"--install-plan can only be Manual or Automatic. Received '{installplan}'.")
            sys.exit(1)

        print(f"Deploying the operator using InstallPlan approval mode '{installplan}'.")

        if deploy_cr:
            print(f"Deploying the operator default CR.")

        print("Deploying the operator.")

        return RunAnsibleRole(locals())

    @AnsibleRole("cluster_deploy_aws_efs")
    @AnsibleMappedParams
    def deploy_aws_efs(self):
        """
        Deploy AWS EFS CSI driver and configure AWS accordingly.

        Assumes that AWS (credentials, Ansible module, Python module) is properly configured in the system.
        """

        return RunAnsibleRole()

    @AnsibleRole("cluster_deploy_minio_s3_server")
    @AnsibleConstant("Name of the user/access key to use to connect to the Minio server",
                     "access_key", "minio")
    @AnsibleConstant("Name of the Minio admin user",
                     "root_user", "admin")
    @AnsibleMappedParams
    def deploy_minio_s3_server(self, secret_properties_file, namespace="minio"):
        """
        Deploy Minio S3 server

        Example of secret properties file:

        user_password=passwd
        admin_password=adminpasswd

        Args:
            secret_properties_file: Path of a file containing the properties of S3 secrets.
            namespace: Namespace in which Minio should be deployed.
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("cluster_deploy_nginx_server")
    @AnsibleMappedParams
    def deploy_nginx_server(self, namespace, directory):
        """
        Deploy an NGINX HTTP server

        Args:
            namespace: namespace where the server will be deployed. Will be create if it doesn't exist.
            directory: directory containing the files to serve on the HTTP server.
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("cluster_deploy_redis_server")
    @AnsibleMappedParams
    def deploy_redis_server(self, namespace):
        """
        Deploy a redis server

        Args:
            namespace: namespace where the server will be deployed. Will be create if it doesn't exist.
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("cluster_prometheus_db")
    @AnsibleConstant("Directory to dump on the Prometheus Pod", "directory", "/prometheus")
    @AnsibleConstant("Prefix to apply to the db name in 'dump' mode", "dump_name_prefix", "prometheus")
    @AnsibleMappedParams
    def reset_prometheus_db(self,
                            mode="reset",
                            label="app.kubernetes.io/component=prometheus",
                            namespace="openshift-monitoring"):
        """
        Resets Prometheus database, by destroying its Pod

        By default, target OpenShift Prometheus Pod.

        Args:
          label: Label to use to identify Prometheus Pod.
          namespace: Namespace where to search Promtheus Pod.
          mode: Mode in which the role will run. Can be 'reset' or 'dump'.
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("cluster_prometheus_db")
    @AnsibleConstant("", "mode", "dump")
    @AnsibleMappedParams
    @AnsibleSkipConfigGeneration # see reset_prometheus_db
    def dump_prometheus_db(self, label="app.kubernetes.io/component=prometheus", namespace="openshift-monitoring", dump_name_prefix="prometheus"):
        """
        Dump Prometheus database into a file

        By default, target OpenShift Prometheus Pod.

        Args:
          label: Label to use to identify Prometheus Pod.
          namespace: Namespace where to search Promtheus Pod.
          dump_name_prefix: Name prefix for the archive that will be stored.
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("cluster_destroy_ocp")
    @AnsibleMappedParams
    def destroy_ocp(self, region="", tag="", confirm=False, tag_value="owned", openshift_install="openshift-install"):
        """
        Destroy an OpenShift cluster

        Args:
          region: The AWS region where the cluster lives. If empty and --confirm is passed, look up from the cluster.
          tag: The resource tag key. If empty and --confirm is passed, look up from the cluster.
          confirm: If the region/label are not set, and --confirm is passed, destroy the current cluster.
          tag_value: The resource tag value.
          openshift_install: The path to the `openshift-install` to use to destroy the cluster. If empty, pick it up from the `deploy-cluster` subproject.
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("cluster_create_osd")
    @AnsibleConstant("Name of the admin account that will be created.",
                     "kubeadmin_name", "kubeadmin")
    @AnsibleConstant("Group that the admin account will be part of.",
                     "kubeadmin_group", "cluster-admins")
    @AnsibleConstant("Name of the worker node machinepool",
                     "machinepool_name", "default")
    @AnsibleMappedParams
    def create_osd(self,
                   cluster_name, secret_file, kubeconfig,
                   version="4.10.15",
                   region="us-east-1",
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
          region: AWS region where the cluster will be deployed.
          version: OpenShift version to deploy.
          htaccess_idp_name: Name of the Identity provider that will be created for the admin account.
          compute_machine_type: Name of the AWS machine instance type that will be used for the compute nodes.
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("cluster_destroy_osd")
    @AnsibleMappedParams
    def destroy_osd(self, cluster_name):
        """
        Destroy an OpenShift Dedicated cluster.

        Args:
          cluster_name: The name of the cluster to destroy.
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("cluster_deploy_ldap")
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

        user_password=passwd
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

    @AnsibleRole("cluster_undeploy_ldap")
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

    @AnsibleRole("cluster_preload_image")
    @AnsibleMappedParams
    def preload_image(self,
                      name, image, namespace="default",
                      node_selector_key="", node_selector_value="",
                      pod_toleration_key="", pod_toleration_effect=""):
        """
        Preload a container image on all the nodes of a cluster.

        Args:
          name: Name to give to the DaemonSet used for preloading the image.
          image: Container image to preload on the nodes.
          namespace: Namespace in which the DaemonSet will be created.
          node_selector_key: NodeSelector key to apply to the DaemonSet.
          node_selector_value: NodeSelector value to apply to the DaemonSet.
          pod_toleration_key: Pod toleration to apply to the DaemonSet.
          pod_toleration_effect: Pod toleration to apply to the DaemonSet.
        """

        toolbox_name_suffix = os.environ.get("ARTIFACT_TOOLBOX_NAME_SUFFIX", "")
        # use `name` as first suffix in the directory name
        os.environ["ARTIFACT_TOOLBOX_NAME_SUFFIX"] = f"_{name}{toolbox_name_suffix}"

        return RunAnsibleRole(locals())

    @AnsibleRole("cluster_create_htpasswd_user")
    @AnsibleConstant("Name of the group that will be created for the user",
                     "groupname", "local-admins")
    @AnsibleConstant("Role that will be given to the user group",
                      "role", "cluster-admin")
    @AnsibleConstant("Name of the htpasswd IDP being created",
                     "htpasswd_idp_name", "htpasswd")
    @AnsibleConstant("Name of the secret that will contain the htpasswd passwords",
                     "secret_name", "htpasswd-secret")
    @AnsibleMappedParams
    def create_htpasswd_adminuser(self, username, passwordfile, wait=False):
        """
        Create an htpasswd admin user.

        Will remove any other existing OAuth.

        Example of password file:
        password=my-strong-password

        Args:
          username: Username of the htpasswd user.
          passwordfile: Password file where the user's password is stored. Will be sourced.
          wait: If True, waits for the user to be able to login into the cluster.
        """

        return RunAnsibleRole(locals())
