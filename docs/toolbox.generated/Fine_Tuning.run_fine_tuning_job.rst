:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Fine_Tuning.run_fine_tuning_job


fine_tuning run_fine_tuning_job
===============================

Run a simple fine-tuning Job.




Parameters
----------


``name``  

* The name of the fine-tuning job to create


``namespace``  

* The name of the namespace where the scheduler load will be generated


``pvc_name``  

* The name of the PVC where the model and dataset are stored


``workload``  

* The name of the workload to run inside the container (fms or ilab)


``model_name``  

* The name of the model to use inside the /dataset directory of the PVC


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


``container_image``  

* The image to use for the fine-tuning container

* default value: ``quay.io/modh/fms-hf-tuning:release-7a8ff0f4114ba43398d34fd976f6b17bb1f665f3``


``gpu``  

* The number of GPUs to request for the fine-tuning job


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


``pod_count``  

* Number of Pods to include in the job

* default value: ``1``


``hyper_parameters``  

* Dictionnary of hyper-parameters to pass to sft-trainer


``capture_artifacts``  

* If enabled, captures the artifacts that will help post-mortem analyses

* default value: ``True``


``sleep_forever``  

* If true, sleeps forever instead of running the fine-tuning command.


``ephemeral_output_pvc_size``  

* If a size (with units) is passed, use an ephemeral volume claim for storing the fine-tuning output. Otherwise, use an emptyDir.


``use_secondary_nic``  

* If enabled, activates the secondary NIC

