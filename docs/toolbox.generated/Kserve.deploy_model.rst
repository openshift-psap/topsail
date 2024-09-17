:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Kserve.deploy_model


kserve deploy_model
===================

Deploy a KServe model




Parameters
----------


``namespace``  

* The namespace in which the model should be deployed


``runtime``  

* Name of the runtime (standalone-tgis or vllm)


``model_name``  

* The name to give to the serving runtime


``sr_name``  

* The name of the ServingRuntime object


``sr_kserve_image``  

* The image of the Kserve serving runtime container


``inference_service_name``  

* The name to give to the inference service


``inference_service_min_replicas``  

* The minimum number of replicas. If none, the field is left unset.
* type: Int


``delete_others``  

* If True, deletes the other serving runtime/inference services of the namespace

* default value: ``True``


``raw_deployment``  

* If True, do not try to configure anything related to Serverless.

