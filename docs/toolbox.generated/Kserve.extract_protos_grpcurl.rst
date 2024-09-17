:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Kserve.extract_protos_grpcurl


kserve extract_protos_grpcurl
=============================

Extracts the protos of an inference service, with GRPCurl observe




Parameters
----------


``namespace``  

* The namespace in which the model was deployed


``inference_service_name``  

* The name of the inference service


``dest_file``  

* The path where the proto file will be stored


``methods``  

* The list of methods to extract
* type: List


``copy_to_artifacts``  

* If True, copy the protos to the command artifacts. If False, don't.

* default value: ``True``

