import sys
import secrets

from toolbox._common import RunAnsibleRole, AnsibleRole


class GPUOperator:
    """
    Commands for deploying, building and testing the GPU operator in various ways
    """

    @AnsibleRole("gpu_operator_deploy_from_operatorhub")
    def deploy_cluster_policy(self):
        """
        Creates the ClusterPolicy from the OLM ClusterServiceVersion
        """
        print("Creating the ClusterPolicy from the CSV")
        return RunAnsibleRole({"gpu_operator_deploy_from": "pre-deployed"})

    @AnsibleRole("gpu_operator_deploy_from_operatorhub")
    def deploy_from_bundle(self, bundle, namespace="nvidia-gpu-operator"):
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
            return RunAnsibleRole("gpu_operator_deploy_from_operatorhub", opts)

        opts["deploy_bundle_image"] = bundle
        return RunAnsibleRole(opts)

    @AnsibleRole("cluster_deploy_operator")
    def deploy_from_operatorhub(self, namespace="nvidia-gpu-operator", version=None, channel=None, installPlan="Manual"):
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
        return RunAnsibleRole(opts)

    @AnsibleRole("gpu_operator_run_gpu-burn")
    def run_gpu_burn(self, runtime=None):
        """
        Runs the GPU burn on the cluster

        Args:
            runtime: How long to run the GPU for, in seconds
        """
        opts = {}
        if runtime is not None:
            opts["gpu_burn_time"] = runtime
            print(f"Running GPU Burn for {runtime} seconds.")

        return RunAnsibleRole(opts)

    @AnsibleRole("gpu_operator_undeploy_from_operatorhub")
    def undeploy_from_operatorhub(self):
        """
        Undeploys a GPU-operator that was deployed from OperatorHub
        """

        return RunAnsibleRole()

    @AnsibleRole("gpu_operator_wait_deployment")
    def wait_deployment(self):
        """
        Waits for the GPU operator to deploy
        """
        return RunAnsibleRole()

    @AnsibleRole("gpu_operator_capture_deployment_state")
    def capture_deployment_state(self):
        """
        Captures the GPU operator deployment state
        """
        return RunAnsibleRole()

    @AnsibleRole("gpu_operator_get_csv_version")
    def get_csv_version(self):
        """
        Get the version of the GPU Operator currently installed from OLM
        Stores the version in the 'ARTIFACT_EXTRA_LOGS_DIR' artifacts directory.
        """

        return RunAnsibleRole()
