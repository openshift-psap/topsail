:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Llm_Load_Test.run


llm_load_test run
=================

Load test the wisdom model




Parameters
----------


``host``  

* The host endpoint of the gRPC call


``port``  

* The gRPC port on the specified host


``duration``  

* The duration of the load testing


``plugin``  

* The llm-load-test plugin to use (tgis_grpc_plugin or caikit_client_plugin for now)

* default value: ``tgis_grpc_plugin``


``interface``  

* (http or grpc) the interface to use for llm-load-test-plugins that support both

* default value: ``grpc``


``model_id``  

* The ID of the model to pass along with the GRPC call

* default value: ``not-used``


``src_path``  

* Path where llm-load-test has been cloned

* default value: ``projects/llm_load_test/subprojects/llm-load-test/``


``streaming``  

* Whether to stream the llm-load-test requests

* default value: ``True``


``use_tls``  

* Whether to set use_tls: True (grpc in Serverless mode)


``concurrency``  

* Number of concurrent simulated users sending requests

* default value: ``16``


``max_input_tokens``  

* Max input tokens in llm load test to filter the dataset

* default value: ``1024``


``max_output_tokens``  

* Max output tokens in llm load test to filter the dataset

* default value: ``512``


``max_sequence_tokens``  

* Max sequence tokens in llm load test to filter the dataset

* default value: ``1536``


``endpoint``  

* Name of the endpoint to query (for openai plugin only)

* default value: ``/v1/completions``

