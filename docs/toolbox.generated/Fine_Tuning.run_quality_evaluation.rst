:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Fine_Tuning.run_quality_evaluation


fine_tuning run_quality_evaluation
==================================

Run a simple fine-tuning Job.




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


``container_image``  

* The image to use for the fine-tuning container

* default value: ``registry.redhat.io/ubi9``


``gpu``  

* The number of GPUs to request for the fine-tuning job


``memory``  

* The number of RAM gigs to request for to the fine-tuning job (in Gigs)

* default value: ``10``


``cpu``  

* The number of CPU cores to request for the fine-tuning job (in cores)

* default value: ``1``


``pod_count``  

* Number of pods to deploy in the job

* default value: ``1``


``hyper_parameters``  

* Dictionnary of hyper-parameters to pass to sft-trainer


``sleep_forever``  

* If true, sleeps forever instead of running the fine-tuning command.

