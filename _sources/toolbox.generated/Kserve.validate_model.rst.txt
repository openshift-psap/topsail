:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Kserve.validate_model


kserve validate_model
=====================

Validate the proper deployment of a KServe model

Warning:
  This command requires `grpcurl` to be available in the PATH.


Parameters
----------


``inference_service_names``  

* A list of names of the inference service to validate


``query_count``  

* Number of query to perform


``runtime``  

* Name of the runtime used (standalone-tgis or vllm)


``model_id``  

* The model-id to pass to the inference service

* default value: ``not-used``


``namespace``  

* The namespace in which the Serving stack was deployed. If empty, use the current project.


``raw_deployment``  

* If True, do not try to configure anything related to Serverless. Works only in-cluster at the moment.


``method``  

* The gRPC method to call #TODO remove?


``proto``  

* If not empty, the proto file to pass to grpcurl

