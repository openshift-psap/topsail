:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Fine_Tuning.ray_fine_tuning_job


fine_tuning ray_fine_tuning_job
===============================

Run a simple Ray fine-tuning Job.




Parameters
----------


``name``  

* The name of the fine-tuning job to create


``namespace``  

* The name of the namespace where the scheduler load will be generated


``pvc_name``  

* The name of the PVC where the model and dataset are stored


``model_name``  

* The name of the model to use inside the /dataset directory of the PVC


``ft_scripts_dir``  

* Directory where the fine-tuning scripts are stored


``dataset_name``  

* The name of the dataset to use inside the /model directory of the PVC


``dataset_replication``  

* Number of replications of the dataset to use, to artificially extend or reduce the fine-tuning effort

* default value: ``1``


``dataset_transform``  

* Name of the transformation to apply to the dataset


``dataset_prefer_cache``  

* If True, and the dataset has to be transformed/duplicated, save and/or load it from the PVC

* default value: ``True``


``dataset_prepare_cache_only``  

* If True, only prepare the dataset cache file and do not run the fine-tuning.


``dataset_response_template``  

* The delimiter marking the beginning of the response in the dataset samples

* default value: ``\n### Label:``


``container_image``  

* The image to use for the fine-tuning container

* default value: ``quay.io/rhoai/ray:2.35.0-py39-cu121-torch24-fa26``


``ray_version``  

* The version identifier passed to the RayCluster object

* default value: ``2.35.0``


``gpu``  

* The number of GPUs to request for the fine-tuning job

* default value: ``1``


``memory``  

* The number of RAM gigs to request for to the fine-tuning job (in Gigs)

* default value: ``10``


``cpu``  

* The number of CPU cores to request for the fine-tuning job (in cores)

* default value: ``1``


``request_equals_limits``  

* If True, sets the 'limits' of the job with the same value as the request.


``prepare_only``  

* If True, only prepare the environment but do not run the fine-tuning job.


``delete_other``  

* If True, delete the other PyTorchJobs before running


``worker_replicas``  

* Number of worker replicas to deploy

* default value: ``2``


``hyper_parameters``  

* Dictionnary of hyper-parameters to pass to sft-trainer


``sleep_forever``  

* If true, sleeps forever instead of running the fine-tuning command.

