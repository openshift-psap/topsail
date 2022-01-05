import sys
import secrets

from toolbox._common import PlaybookRun


class GPUOperator:
    """
    Commands for deploying, building and testing the GPU operator in various ways
    """

    @staticmethod
    def deploy_cluster_policy():
        """
        Creates the ClusterPolicy from the OLM ClusterServiceVersion
        """
        print("Creating the ClusterPolicy from the CSV")
        return PlaybookRun(
            "gpu_operator_deploy_from_operatorhub",
            {"gpu_operator_deploy_from": "pre-deployed"},
        )

    @staticmethod
    def deploy_from_bundle(bundle, namespace="nvidia-gpu-operator"):
        """
        Deploys the GPU Operator from a bundle

        Args:
            bundle: Either a bundle OCI image or "master" to deploy the latest bundle
            namespace: Optional namespace in which the GPU Operator will be deployed. Before v1.9, the value must be "openshift-operators". With >=v1.9, the namespace can freely chosen (except 'openshift-operators'). Default: nvidia-gpu-operator.
        """
        opts = {"gpu_operator_deploy_from": "bundle",
                "gpu_operator_target_namespace": namespace}

        if bundle == 'master':
            print("Deploying the GPU Operator from OperatorHub using the master bundle")
            return PlaybookRun("gpu_operator_deploy_from_operatorhub", opts)

        opts["deploy_bundle_image"] = bundle
        return PlaybookRun("gpu_operator_deploy_from_operatorhub", opts)

    @staticmethod
    def deploy_from_operatorhub(namespace="nvidia-gpu-operator", version=None, channel=None, installPlan="Manual"):
        """
        Deploys the GPU operator from OperatorHub

        Args:
            namespace: Optional namespace in which the GPU Operator will be deployed. Before v1.9, the value must be "openshift-operators". With >=v1.9, the namespace can freely chosen. Default: nvidia-gpu-operator.
            channel: Optional channel to deploy from. If unspecified, deploys the CSV's default channel.
            version: Optional version to deploy. If unspecified, deploys the latest version available in the selected channel. Run the toolbox gpu_operator list_version_from_operator_hub subcommand to see the available versions.
            installPlan: Optional InstallPlan approval mode (Automatic or Manual [default])
        """

        opts = {
            "cluster_deploy_operator_catalog": "certified-operators",
            "cluster_deploy_operator_manifest_name": "gpu-operator-certified",

            "cluster_deploy_operator_namespace": namespace,
            "cluster_deploy_operator_all_namespaces": namespace == "openshift-operators",

            "cluster_deploy_operator_deploy_cr": True,
            "cluster_deploy_operator_namespace_monitoring": True,
        }

        if channel is not None:
            opts["cluster_deploy_operator_channel"] = channel
            print(
                f"Deploying the GPU Operator from OperatorHub using channel '{channel}'."
            )

        if version is not None:
            if channel is None:
                print("Version may only be specified if --channel is specified")
                sys.exit(1)

            opts["cluster_deploy_operator_version"] = version
            print(
                f"Deploying the GPU Operator from OperatorHub using version '{version}'."
            )

        opts["cluster_deploy_operator_installplan_approval"] = installPlan
        if installPlan not in ("Manual", "Automatic"):
            print(
                f"InstallPlan can only be Manual or Automatic. Received '{installPlan}'."
            )
            sys.exit(1)

        print(
            f"Deploying the GPU Operator from OperatorHub using InstallPlan approval '{installPlan}'."
        )

        print("Deploying the GPU Operator from OperatorHub.")
        return PlaybookRun("cluster_deploy_operator", opts)

    @staticmethod
    def run_gpu_burn(runtime=None):
        """
        Runs the GPU burn on the cluster

        Args:
            runtime: How long to run the GPU for, in seconds
        """
        opts = {}
        if runtime is not None:
            opts["gpu_burn_time"] = runtime
            print(f"Running GPU Burn for {runtime} seconds.")

        return PlaybookRun("gpu_operator_run_gpu-burn", opts)

    @staticmethod
    def set_repo_config(repo_file, dest_dir=None):
        """
        Sets the GPU-operator driver yum repo configuration file

        Args:
            repo_file: Absolute path to the repo file
            dest_dir: The destination dir in the pod to place the repo in
        """
        opts = {"gpu_operator_set_repo_filename": repo_file}
        if dest_dir is not None:
            opts["gpu_operator_set_repo_destdir"] = dest_dir

        return PlaybookRun("gpu_operator_set_repo-config", opts)

    @staticmethod
    def undeploy_from_commit():
        """
        Undeploys a GPU-operator that was deployed from a commit
        """

        return PlaybookRun("gpu_operator_undeploy_custom_commit")

    @staticmethod
    def undeploy_from_operatorhub():
        """
        Undeploys a GPU-operator that was deployed from OperatorHub
        """

        return PlaybookRun("gpu_operator_undeploy_from_operatorhub")

    @staticmethod
    def wait_deployment():
        """
        Waits for the GPU operator to deploy
        """
        return PlaybookRun("gpu_operator_wait_deployment")

    @staticmethod
    def capture_deployment_state():
        """
        Captures the GPU operator deployment state
        """
        return PlaybookRun("gpu_operator_capture-deployment-state")

    @staticmethod
    def cleanup_bundle_from_commit():
        """
        Cleanup resources leftover from building a bundle from a commit
        """
        return PlaybookRun("gpu_operator_cleanup_bundle_from_commit")

    @staticmethod
    def bundle_from_commit(
        git_repo,
        git_ref,
        quay_push_secret,
        quay_image_name,
        tag_uid=None,
        namespace=None,
        with_validator=False,
        with_driver=False,
        publish_to_quay=False
    ):
        """
        Build an image of the GPU Operator from sources (<git repository> <git reference>)
        and push it to quay.io <quay_image_image>:operator_bundle_gpu-operator-<gpu_operator_image_tag_uid>
        using the <quay_push_secret> credentials.

        Example parameters - https://github.com/NVIDIA/gpu-operator.git master /path/to/quay_secret.yaml quay.io/org/image_name

        See 'oc get imagestreamtags -n gpu-operator-ci -oname' for the tag-uid to reuse.

        Args:
            git_repo: Git repository URL to generate bundle of
            git_ref: Git ref to bundle
            quay_push_secret: A file Kube Secret YAML file with `.dockerconfigjson` data and type kubernetes.io/dockerconfigjson
            quay_image_image: The quay repo to push to
            tag_uid: Optional image tag suffix to use.
            namespace: Optional namespace to use to deploy the GPU Operator. Default: nvidia-gpu-operator
            with_validator: Optional flag to enable building the validator image (default: false)
            with_driver: Optional flag to enable building the driver image (default: false)
            publish_to_quay: Optional flag to publish the full bundle (including images) to Quay.io (default: false)
        """
        if tag_uid is None:
            tag_uid = secrets.token_hex(4)

        def to_y(_s):
            if not _s: return ""
            if isinstance(_s, bool): return "y" # can't be false here
            s = str(_s).lower()
            if s == "false": return ""
            if s == "n": return ""
            if s == "no": return ""
            return "y"

        opts = {
            "gpu_operator_git_repo": git_repo,
            "gpu_operator_git_ref": git_ref,
            "gpu_operator_image_tag_uid": tag_uid,
            "gpu_operator_commit_quay_push_secret": quay_push_secret,
            "gpu_operator_commit_quay_image_name": quay_image_name,
            "gpu_operator_with_driver": to_y(with_driver),
            "gpu_operator_with_validator": to_y(with_validator),
            "gpu_operator_publish_to_quay":  to_y(publish_to_quay),
        }

        if namespace is not None:
            opts["gpu_operator_target_namespace"] = namespace

        return PlaybookRun("gpu_operator_bundle_from_commit", opts)

    @staticmethod
    def get_csv_version():
        """
        Get the version of the GPU Operator currently installed from OLM
        Stores the version in the 'ARTIFACT_EXTRA_LOGS_DIR' artifacts directory.
        """

        return PlaybookRun("gpu_operator_get_csv_version")

    @staticmethod
    def prepare_test_alerts(alert_delay=1, alert_prefix="CI"):
        """
        Prepare test alerts based on the existing GPU Operator alerts.
        Test alerts have a shorter delay than default alerts.

        Args:
          alert_delay: Delay (in minutes) before the alerts fire.
          alert_prefix: Prefix to prepend to the alert names, to distinguish them from the normal alerts.
        """

        opts = {
            "gpu_operator_test_alerts_delay": alert_delay,
            "gpu_operator_test_alerts_prefix": alert_prefix,
        }

        return PlaybookRun("gpu_operator_prepare_test_alerts", opts)
