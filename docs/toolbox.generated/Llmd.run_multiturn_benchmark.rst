:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Llmd.run_multiturn_benchmark


llmd run_multiturn_benchmark
============================

Runs a multi-turn benchmark job against the LLM inference service




Parameters
----------


``llmisvc_name``  

* Name of the LLMInferenceService to benchmark (in same namespace)


``name``  

* Name of the benchmark job

* default value: ``multi-turn-benchmark``


``namespace``  

* Namespace to run the benchmark job in (empty string auto-detects current namespace)


``image``  

* Container image for the benchmark

* default value: ``quay.io/hayesphilip/multi-turn-benchmark``


``version``  

* Version tag for the benchmark image

* default value: ``0.0.1``


``timeout``  

* Timeout in seconds to wait for job completion

* default value: ``900``


``parallel``  

* Number of parallel connections

* default value: ``9``

