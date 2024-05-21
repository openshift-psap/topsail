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
            container_image="quay.io/modh/fms-hf-tuning:01b3824c9aba22d9d0695399681e6f0507840e7f",

            gpu=0,
            memory=10,
            cpu=1,
            request_equals_limits=False,

            per_device_train_batch_size=4,
            per_device_eval_batch_size=4,
            use_flash_attn=False,

            prepare_only=False,
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
          container_image: the image to use for the fine-tuning container
          gpu: the number of GPUs to request for the fine-tuning job
          memory: the number of RAM gigs to request for to the fine-tuning job (in Gigs)
          cpu: the number of CPU cores to request for the fine-tuning job (in cores)
          request_equals_limits: if True, sets the 'limits' of the job with the same value as the request.

          per_device_train_batch_size: batch size to use for the model fine-tuning training
          per_device_eval_batch_size: batch size to use for the model fine-tuning evaluation
          use_flash_attn: Enables/disables Flash Attention

          prepare_only: if True, only prepare the environment but do not run the fine-tuning job.
        """

        return RunAnsibleRole(locals())
