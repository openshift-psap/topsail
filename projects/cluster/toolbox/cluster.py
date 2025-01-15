import os
import sys
import logging

from projects.core.library.ansible_toolbox import (
    RunAnsibleRole, AnsibleRole,
    AnsibleMappedParams, AnsibleConstant,
    AnsibleSkipConfigGeneration
)

class Cluster:
    """
    Commands relating to cluster scaling, upgrading and environment capture
    """

    @AnsibleRole("cluster_set_scale")
    def set_scale(self, instance_type, scale, base_machineset="", force=False, taint="", name="", spot=False, disk_size=None):
        """
        Ensures that the cluster has exactly `scale` nodes with instance_type `instance_type`

        If the machinesets of the given instance type already have the required total number of replicas,
        their replica parameters will not be modified.
        Otherwise,
        - If there's only one machineset with the given instance type, its replicas will be set to the value of this parameter.
        - If there are other machinesets with non-zero replicas, the playbook will fail, unless the `force` parameter is
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
            spot: Set to true to request spot instances from AWS. Set to false (default) to request on-demand instances.
            disk_size: Size of the EBS volume to request for the root partition
        """
        opts = {
            "machineset_instance_type": instance_type,
            "scale": scale,
            "machineset_taint": taint,
            "machineset_name": name,
            "cluster_ensure_machineset_base_machineset": base_machineset,
            "force_scale": force,
            "cluster_ensure_machineset_spot": spot or False,
            "cluster_ensure_machineset_disk_size": disk_size,
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
                        catalog_namespace="openshift-marketplace",
                        deploy_cr: bool = False,
                        namespace_monitoring: bool = False,
                        all_namespaces: bool = False,
                        config_env_names: list = [],
                        csv_base_name=None,
                        ):
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
            catalog_namespace: Namespace in which the CatalogSource will be deployed
            config_env_names: If not empty, a list of config env names to pass to the subscription
            csv_base_name: if not empty, base name of the CSV. If empty, use the manifest_name.
        """

        if namespace == "all":
            all_namespaces = True
            namespace = "openshift-operators"

            if namespace_monitoring:
                print("Namespace monitoring cannot be enabled when deploying in all the namespaces.")
                sys.exit(1)

            print("Deploying the operator in all the namespaces.")

        if namespace_monitoring:
            print("Enabling namespace monitoring.")

        print(f"Deploying the operator using namespace '{namespace}'.")

        if channel:
            print(f"Deploying the operator using channel '{channel}'.")

        if version:
            if channel:
                print("Version may only be specified if --channel is specified")
                sys.exit(1)

            print(f"Deploying the operator using version '{version}'.")

        if installplan_approval not in ("Manual", "Automatic"):
            print(f"--install-plan can only be Manual or Automatic. Received '{installplan_approval}'.")
            sys.exit(1)

        print(f"Deploying the operator using InstallPlan approval mode '{installplan_approval}'.")

        if deploy_cr:
            print("Deploying the operator default CR.")

        print("Deploying the operator.")

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
    @AnsibleSkipConfigGeneration  # see reset_prometheus_db
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

    @AnsibleRole("cluster_query_prometheus_db")
    @AnsibleMappedParams
    def query_prometheus_db(
            self,
            promquery_file,
            dest_dir,
            namespace,
            duration_s=0,
            start_ts=None,
            end_ts=None,
    ):
        """
        Query Prometheus with a list of PromQueries read in a file

        The metrics_file is a multi-line list, with first the name of the metric, prefixed with '#'
        Then the definition of the metric, than can spread on multiple lines, until the next # is found.

        Example:
        ::

          promquery_file:
            # sutest__cluster_cpu_capacity
            sum(cluster:capacity_cpu_cores:sum)
            # sutest__cluster_memory_requests
               sum(
                    kube_pod_resource_request{resource="memory"}
                    *
                    on(node) group_left(role) (
                      max by (node) (kube_node_role{role=~".+"})
                    )
                  )
            # openshift-operators CPU request
            sum(kube_pod_container_resource_requests{namespace=~'openshift-operators',resource='cpu'})
            # openshift-operators CPU limit
            sum(kube_pod_container_resource_limits{namespace=~'openshift-operators',resource='cpu'})
            # openshift-operators CPU usage
            sum(rate(container_cpu_usage_seconds_total{namespace=~'openshift-operators'}[5m]))

        Args:
          promquery_file: file where the Prometheus Queries are stored. See the example above to understand the format.
          dest_dir: directory where the metrics should be stored
          duration_s: the duration of the history to query
          namespace: the namespace where the metrics should searched for
          start_ts: the start timestamp of the history to query. Incompatible with duration_s flag.
          end_ts: the end timestamp of the history to query. Incompatible with duration_s flag.
        """

        if duration_s and (start_ts or end_ts):
            logging.error(f"duration_s={duration_s} and start_ts={start_ts}/end_ts={end_ts} cannot be passed together")
            sys.exit(1)

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
                   compute_nodes: int = 2,
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

    @AnsibleRole("cluster_set_project_annotation")
    @AnsibleMappedParams
    def set_project_annotation(self, key, value=None, project=None, all=False):
        """
        Set an annotation on a given project, or for any new projects.

        Args:
          key: The annotation key
          value: The annotation value. If value is omited, the annotation is removed.
          project: The project to annotate. Must be set unless --all is passed.
          all: If set, the annotation will be set for any new project.
        """

        if all and project:
            print(f"ERROR: --project cannot be both set if --all is set.")
            sys.exit(1)

        if not all and not project:
            print(f"ERROR: --project must be set, unless --all is set.")
            sys.exit(1)

        return RunAnsibleRole(locals())


    @AnsibleRole("cluster_fill_workernodes")
    @AnsibleMappedParams
    def fill_workernodes(self, namespace="default", name="resource-placeholder", label_selector="node-role.kubernetes.io/worker"):
        """
        Fills the worker nodes with place-holder Pods with the maximum available amount of a given resource name.

        Args:
          namespace: namespace in which the place-holder Pods should be deployed
          name: name prefix to use for the place-holder Pods
          label_selector: label to use to select the nodes to fill
        """

        return RunAnsibleRole(locals())


    @AnsibleRole("cluster_update_pods_per_node")
    @AnsibleMappedParams
    def update_pods_per_node(self,
                             max_pods=250,
                             pods_per_core=10,
                             name="set-max-pods",
                             label="pools.operator.machineconfiguration.openshift.io/worker",
                             label_value="",
                             pod_pids_limit=4096
                             ):
        """
        Update the maximum number of Pods per Nodes, and Pods per Core
        See alse:
          https://docs.openshift.com/container-platform/4.14/nodes/nodes/nodes-nodes-managing-max-pods.html

        Args:
          max_pods: the maximum number of Pods per nodes
          pods_per_core: the maximum number of Pods per core
          name: the name to give to the KubeletConfig object
          label: the label selector for the nodes to update
          label_value: the expected value for the label selector
          pod_pids_limit: limit the maximum number of processes that can be created by containers within a pod
        """

        return RunAnsibleRole(locals())


    @AnsibleRole("cluster_build_push_image")
    @AnsibleMappedParams
    def build_push_image(
            self,
            image_local_name,
            tag,
            namespace,
            remote_repo="",
            remote_auth_file="",
            git_repo="",
            git_ref="",
            dockerfile_path="Dockerfile",
            context_dir="/",
            memory: float = "",
            from_image = None,
            from_imagetag = None,
    ):
        """
        Build and publish an image to quay using either a Dockerfile or
        git repo.

        Args:
            image_local_name: Name of locally built image.
            tag: Tag for the image to build.
            namespace: Namespace where the local image will be built.
            remote_repo: Remote image repo to push to. If undefined, the image will not be pushed.
            remote_auth_file: Auth file for the remote repository.

            git_repo: Git repo containing Dockerfile if used as source. If undefined, the local path of 'dockerfile_path' will be used.
            git_ref: Git commit ref (branch, tag, commit hash) in the git repository.

            context_dir: Context dir inside the git repository.
            dockerfile_path: Path/Name of Dockerfile if used as source. If 'git_repo' is undefined, this path will be resolved locally, and the Dockerfile will be injected in the image BuildConfig.
            memory: Flag to specify the required memory to build the image (in Gb).
            from_image: Base image to use, instead of the FROM image specified in the Dockerfile.
            from_imagetag: Base imagestreamtag to use, instead of the FROM image specified in the Dockerfile.
        """

        if not git_repo and not dockerfile_path:
            logging.error("Either a git repo or a Dockerfile Path is required")
            sys.exit(1)

        both_or_none = lambda a, b: (a and b) or (not a and not b)

        if not both_or_none(remote_repo, remote_auth_file):
            logging.error("remote_repo and remote_auth_file must come together.")
            sys.exit(1)

        elif remote_repo:
            logging.info(f"Using remote repo {remote_repo} and auth file {remote_auth_file} to push the image.")
        else:
            logging.info(f"No remote repo provided, not pushing the image.")

        if not both_or_none(git_repo, git_ref):
            logging.error("git_repo and git_ref must come together.")
            sys.exit(1)

        elif git_repo:
            logging.info(f"Using Git repo {git_repo}|{git_ref}|{context_dir}|{dockerfile_path} for building the image.")
        else:
            logging.info(f"Using local dockerfile at {dockerfile_path} for building the image.")

        if not git_repo and context_dir != "/":
            logging.error("local builds (no git_repo) cannot specify a context_dir.")
            sys.exit(1)

        if memory:
            try:
                memory = str(float(memory))
                logging.info(f"Requesting {memory} of memory for building the image.")
            except ValueError:
                logging.error("memory must be of type float or int")
                sys.exit(1)

        if "/" in tag or "_" in tag:
            logging.error(f"the tag ('{tag}') cannot contain '/' or '_' characters")
            sys.exit(1)

        toolbox_name_suffix = os.environ.get("ARTIFACT_TOOLBOX_NAME_SUFFIX", "")
        # use `{image_local_name}_{tag}` as first suffix in the directory name
        os.environ["ARTIFACT_TOOLBOX_NAME_SUFFIX"] = f"_{image_local_name}_{tag}{toolbox_name_suffix}"

        del both_or_none

        if from_image and from_imagetag:
            logging.error(f"the --from-image={from_image} and --from-imagetag={from_imagetag} flags cannot be used at the same time.")
            sys.exit(1)

        return RunAnsibleRole(locals())


    @AnsibleRole("cluster_wait_fully_awake")
    @AnsibleMappedParams
    def wait_fully_awake(self):
        """
        Waits for the cluster to be fully awake after Hive restart
        """

        return RunAnsibleRole(locals())
