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

            model_name,

            dataset_name,
            dataset_replication=1,
            dataset_transform=None,
            dataset_prefer_cache=True,
            dataset_prepare_cache_only=False,
            dataset_response_template="\n### Label:",
            container_image="quay.io/modh/fms-hf-tuning:release-7a8ff0f4114ba43398d34fd976f6b17bb1f665f3",

            gpu=0,
            memory=10,
            cpu=1,
            request_equals_limits=False,

            prepare_only=False,
            delete_other=False,

            worker_replicas=0,

            hyper_parameters={},

            sleep_forever=False,
    ):
        """
        Run a simple fine-tuning Job.

        Args:
          name: the name of the fine-tuning job to create
          namespace: the name of the namespace where the scheduler load will be generated
          pvc_name: the name of the PVC where the model and dataset are stored

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

          prepare_only: if True, only prepare the environment but do not run the fine-tuning job.
          delete_other: if True, delete the other PyTorchJobs before running

          worker_replicas: number of worker replicas to deploy

          hyper_parameters: dictionnary of hyper-parameters to pass to sft-trainer

          sleep_forever: if true, sleeps forever instead of running the fine-tuning command.
        """

        return RunAnsibleRole(locals())


    @AnsibleRole("fine_tuning_run_quality_evaluation")
    @AnsibleMappedParams
    def run_quality_evaluation(
            self,
            name,
            namespace,
            pvc_name,

            model_name,

            container_image="quay.io/rh-ee-kelchen/lm-eval",

            gpu=0,
            memory=10,
            cpu=1,

            worker_replicas=0,

            hyper_parameters={},

            sleep_forever=False,
    ):
        """
        Run a simple fine-tuning Job.

        Args:
          name: the name of the fine-tuning job to create
          namespace: the name of the namespace where the scheduler load will be generated
          pvc_name: the name of the PVC where the model and dataset are stored

          model_name: the name of the model to use inside the /dataset directory of the PVC

          container_image: the image to use for the fine-tuning container
          gpu: the number of GPUs to request for the fine-tuning job
          memory: the number of RAM gigs to request for to the fine-tuning job (in Gigs)
          cpu: the number of CPU cores to request for the fine-tuning job (in cores)

          worker_replicas: number of worker replicas to deploy

          hyper_parameters: dictionnary of hyper-parameters to pass to sft-trainer

          sleep_forever: if true, sleeps forever instead of running the fine-tuning command.
        """

        return RunAnsibleRole(locals())
