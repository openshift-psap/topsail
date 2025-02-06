import sys

from projects.core.library.ansible_toolbox import (
    RunAnsibleRole, AnsibleRole,
    AnsibleMappedParams, AnsibleConstant,
    AnsibleSkipConfigGeneration
)

class Fine_Tuning:
    """
    Commands relating to RHOAI scheduler testing
    """

    @AnsibleRole("fine_tuning_run_fine_tuning_job")
    @AnsibleMappedParams
    def run_fine_tuning_job(
            self,
            name,
            namespace,
            pvc_name,

            workload,

            model_name,
            dataset_name,
            dataset_replication=1,
            dataset_transform=None,
            dataset_prefer_cache=True,
            dataset_prepare_cache_only=False,
            dataset_response_template=None,
            container_image="quay.io/modh/fms-hf-tuning:release-7a8ff0f4114ba43398d34fd976f6b17bb1f665f3",

            gpu=0,
            memory=10,
            cpu=1,
            request_equals_limits=False,
            shared_memory=None,
            prepare_only=False,
            delete_other=False,

            pod_count=1,

            hyper_parameters={},

            capture_artifacts=True,
            sleep_forever=False,

            ephemeral_output_pvc_size=None,
            use_primary_nic=True,
            use_secondary_nic=False,
            use_host_network=False,

            retrieve_files=True,
    ):
        """
        Run a simple fine-tuning Job.

        Args:
          name: the name of the fine-tuning job to create
          namespace: the name of the namespace where the scheduler load will be generated
          pvc_name: the name of the PVC where the model and dataset are stored
          workload: the name of the workload to run inside the container (fms or ilab)

          model_name: the name of the model to use inside the /dataset directory of the PVC

          dataset_name: the name of the dataset to use inside the /model directory of the PVC
          dataset_replication: number of replications of the dataset to use, to artificially extend or reduce the fine-tuning effort
          dataset_transform: name of the transformation to apply to the dataset
          dataset_prefer_cache: if True, and the dataset has to be transformed/duplicated, save and/or load it from the PVC
          dataset_prepare_cache_only: if True, only prepare the dataset cache file and do not run the fine-tuning.
          dataset_response_template: the delimiter marking the beginning of the response in the dataset samples
          container_image: the image to use for the fine-tuning container
          gpu: the number of GPUs to request for the fine-tuning job
          memory: the number of RAM gigs to request for to the fine-tuning job (in Gigs)
          cpu: the number of CPU cores to request for the fine-tuning job (in cores)
          request_equals_limits: if True, sets the 'limits' of the job with the same value as the request.
          shared_memory:  amount of shm (in GB) to give to each of the job pods
          prepare_only: if True, only prepare the environment but do not run the fine-tuning job.
          delete_other: if True, delete the other PyTorchJobs before running

          pod_count: number of Pods to include in the job

          hyper_parameters: dictionnary of hyper-parameters to pass to sft-trainer

          capture_artifacts: if enabled, captures the artifacts that will help post-mortem analyses
          sleep_forever: if true, sleeps forever instead of running the fine-tuning command.

          ephemeral_output_pvc_size: if a size (with units) is passed, use an ephemeral volume claim for storing the fine-tuning output. Otherwise, use an emptyDir.
          use_primary_nic: if enabled, tell NCCL to use the primary NIC. Only taken into account if --use_secondary_nic is passed.
          use_secondary_nic: if enabled, activates the secondary NIC. Can be a list with the name of multiple NetworkDefinitionAttachements, in the same namespace.
          use_host_network: if enabled, activates the host network

          retrieve_files: if enabled, allows files retrieval from the pod to the artifacts directory.
        """

        if use_host_network and use_secondary_nic:
            raise ValueError("Cannot use  --use_host_network and --use_secondary_nic simultaneously.")

        return RunAnsibleRole(locals())


    @AnsibleRole("fine_tuning_ray_fine_tuning_job")
    @AnsibleMappedParams
    def ray_fine_tuning_job(
            self,
            name,
            namespace,
            pvc_name=None,

            model_name=None,
            workload="ray-finetune-llm-deepspeed",

            dataset_name=None,
            dataset_replication=1,
            dataset_transform=None,
            dataset_prefer_cache=True,
            dataset_prepare_cache_only=False,
            container_image="quay.io/rhoai/ray:2.35.0-py39-cu121-torch24-fa26",
            ray_version="2.35.0",
            gpu=0,
            memory=10,
            cpu=1,
            request_equals_limits=False,

            prepare_only=False,
            delete_other=False,

            pod_count=1,

            hyper_parameters={},

            sleep_forever=False,
            capture_artifacts=True,

            shutdown_cluster=True,

            node_selector_key=None,
            node_selector_value=None,

            use_secondary_nic=False,

            ephemeral_output_pvc_size=None,

    ):
        """
        Run a simple Ray fine-tuning Job.

        Args:
          name: the name of the fine-tuning job to create
          namespace: the name of the namespace where the scheduler load will be generated
          pvc_name: the name of the PVC where the model and dataset are stored

          model_name: the name of the model to use inside the /dataset directory of the PVC

          ft_scripts_dir: directory where the fine-tuning scripts are stored

          dataset_name: the name of the dataset to use inside the /model directory of the PVC
          dataset_replication: number of replications of the dataset to use, to artificially extend or reduce the fine-tuning effort
          dataset_transform: name of the transformation to apply to the dataset
          dataset_prefer_cache: if True, and the dataset has to be transformed/duplicated, save and/or load it from the PVC
          dataset_prepare_cache_only: if True, only prepare the dataset cache file and do not run the fine-tuning.
          container_image: the image to use for the fine-tuning container
          gpu: the number of GPUs to request for the fine-tuning job
          memory: the number of RAM gigs to request for to the fine-tuning job (in Gigs)
          cpu: the number of CPU cores to request for the fine-tuning job (in cores)
          request_equals_limits: if True, sets the 'limits' of the job with the same value as the request.

          prepare_only: if True, only prepare the environment but do not run the fine-tuning job.
          delete_other: if True, delete the other PyTorchJobs before running

          pod_count: number of Pods to include in the job

          hyper_parameters: dictionnary of hyper-parameters to pass to sft-trainer

          sleep_forever: if true, sleeps forever instead of running the fine-tuning command.
          ray_version: the version identifier passed to the RayCluster object
          capture_artifacts: if enabled, captures the artifacts that will help post-mortem analyses

          workload: the name of the workload job to run (see the role's workload directory)

          shutdown_cluster: if True, let the RayJob shutdown the RayCluster when the job terminates

          node_selector_key: name of a label to select the node on which this job can run
          node_selector_value: value of the label to select the node on which this job can run

          use_secondary_nic: if enabled, activates the secondary NIC. Can be a list with the name of multiple NetworkDefinitionAttachements, in the same namespace.

          ephemeral_output_pvc_size: if a size (with units) is passed, use an ephemeral volume claim for storing the fine-tuning output. Otherwise, use an emptyDir.
        """

        if dataset_name is None:
            dataset_replication = None

        return RunAnsibleRole(locals())
