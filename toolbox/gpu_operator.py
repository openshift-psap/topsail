import sys
import secrets

from toolbox._common import PlaybookRun


class GPUOperator:
    """
    Commands for deploying, building and testing the GPU operator in various ways
    """
    @staticmethod
    def deploy_from_commit(git_repository, git_reference, tag_uid=None):
        """
        Deploys the GPU operator from the given git commit

        Args:
            git_repository: The git repository to deploy from, e.g. https://github.com/NVIDIA/gpu-operator.git
            git_reference: The git ref to deploy from, e.g. master
            tag_uid: The GPU operator image tag UID. See 'oc get imagestreamtags -n gpu-operator-ci -oname' for the tag-uid to reuse
        """

        if tag_uid is None:
            tag_uid = secrets.token_hex(4)

        opts = {
            "gpu_operator_git_repo": git_repository,
            "gpu_operator_git_ref": git_reference,
            "gpu_operator_image_tag_uid": tag_uid,
        }

        return PlaybookRun("gpu_operator_deploy_custom_commit", opts)

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
    def deploy_from_bundle(bundle):
        """
        Deploys the GPU Operator from a bundle

        Args:
            bundle: Either a bundle OCI image or "master" to deploy the latest bundle
        """
        opts = {"gpu_operator_deploy_from": "bundle"}

        if bundle == 'master':
            print("Deploying the GPU Operator from OperatorHub using the master bundle")
            return PlaybookRun("gpu_operator_deploy_from_operatorhub", opts)

        opts["deploy_bundle_image"] = bundle
        return PlaybookRun("gpu_operator_deploy_from_operatorhub", opts)

    @staticmethod
    def deploy_from_operatorhub(version=None, channel=None, installPlan="Manual"):
        """
        Deploys the GPU operator from OperatorHub

        Args:
            version: The version to deploy. If unspecified, deploys the latest version available in OperatorHub. Run the toolbox gpu_operator list_version_from_operator_hub subcommand to see the available versions.
            channel: Optional channel to deploy from.
            installPlan: Optional InstallPlan approval mode (Automatic or Manual [default])
        """
        opts = {}

        if version is not None:
            opts["gpu_operator_operatorhub_version"] = version
            print(
                f"Deploying the GPU Operator from OperatorHub using version '{version}'."
            )

        if channel is not None:
            if version is None:
                print("Channel may only be specified if --version is specified")
                sys.exit(1)

            opts["gpu_operator_operatorhub_channel"] = channel
            print(
                f"Deploying the GPU Operator from OperatorHub using channel '{channel}'."
            )

        opts["gpu_operator_installplan_approval"] = installPlan
        if installPlan not in ("Manual", "Automatic"):
            print(
                f"InstallPlan can only be Manual or Automatic. Received '{installPlan}'."
            )
            sys.exit(1)

        print(
            f"Deploying the GPU Operator from OperatorHub using InstallPlan approval '{installPlan}'."
        )

        print("Deploying the GPU Operator from OperatorHub using its master bundle.")
        return PlaybookRun("gpu_operator_deploy_from_operatorhub", opts)

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
            tag_uid: The image tag suffix to use.
        """
        if tag_uid is None:
            tag_uid = secrets.token_hex(4)

        opts = {
            "gpu_operator_git_repo": git_repo,
            "gpu_operator_git_ref": git_ref,
            "gpu_operator_image_tag_uid": tag_uid,
            "gpu_operator_commit_quay_push_secret": quay_push_secret,
            "gpu_operator_commit_quay_image_name": quay_image_name,
        }

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
