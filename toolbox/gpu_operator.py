import sys
import secrets

from toolbox._common import RunAnsibleRole, AnsibleRole, AnsibleMappedParams, AnsibleConstant, AnsibleSkipConfigGeneration

class GPU_Operator:
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

    @AnsibleRole("gpu_operator_run_gpu_burn")
    @AnsibleMappedParams
    def run_gpu_burn(self,
                     namespace="default",
                     runtime : int = 30,
                     keep_resources: bool = False,
                     ensure_has_gpu: bool = True,
                     ):
        """
        Runs the GPU burn on the cluster

        Args:
          namespace: namespace in which GPU-burn will be executed
          runtime: How long to run the GPU for, in seconds
          keep_resources: if true, do not delete the GPU-burn ConfigMaps
          ensure_has_gpu: if true, fails if no GPU is available in the cluster.
        """

        return RunAnsibleRole(locals())

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

    @AnsibleRole("gpu_operator_wait_stack_deployed")
    @AnsibleMappedParams
    def wait_stack_deployed(self, namespace="nvidia-gpu-operator"):
        """
        Waits for the GPU Operator stack to be deployed on the GPU nodes

        Args:
          namespace: namespace in which the GPU Operator is deployed
        """

        return RunAnsibleRole(locals())


    @AnsibleRole("gpu_operator_enable_time_sharing")
    @AnsibleMappedParams
    def enable_time_sharing(self, replicas, namespace="nvidia-gpu-operator", configmap_name="time-slicing-config-all"):
        """
        Enable time-sharing in the GPU Operator ClusterPolicy

        Args:
          namespace: namespace in which the GPU Operator is deployed
          replicas: number of slices available for each of the GPUs
          configmap_name: name of the ConfigMap where the configuration will be stored
        """

        return RunAnsibleRole(locals())


    @AnsibleRole("gpu_operator_extend_metrics")
    @AnsibleMappedParams
    def extend_metrics(self,
                       include_defaults=True,
                       include_well_known=False,
                       namespace="nvidia-gpu-operator",
                       configmap_name="metrics-config",
                       extra_metrics : list = None,
                        ):
        """
        Enable time-sharing in the GPU Operator ClusterPolicy

        Args:
          namespace: namespace in which the GPU Operator is deployed
          configmap_name: name of the ConfigMap where the configuration will be stored
          include_defaults: if True, include the default DCGM metrics in the custom config
          include_well_known: if True, include well-known interesting DCGM metrics in the custom config
          extra_metrics: if not None, a [{name,type,description}*] list of dictionnaries with the extra metrics to include in the custom config
        """

        return RunAnsibleRole(locals())
