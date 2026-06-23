:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Llmd.run_guidellm_benchmark


llmd run_guidellm_benchmark
===========================

Runs a Guidellm benchmark job against the LLM inference service




Parameters
----------


``endpoint_url``  

* Endpoint URL for the LLM inference service to benchmark


``name``  

* Name of the benchmark job

* default value: ``guidellm-benchmark``


``namespace``  

* Namespace to run the benchmark job in (empty string auto-detects current namespace)


``image``  

* Container image for the benchmark

* default value: ``ghcr.io/vllm-project/guidellm``


``version``  

* Version tag for the benchmark image

* default value: ``v0.6.0``


``timeout``  

* Timeout in seconds to wait for job completion

* default value: ``900``


``pvc_size``  

* Size of the PersistentVolumeClaim for storing results

* default value: ``1Gi``


``guidellm_args``  

* List of additional guidellm arguments (e.g., ["--rate=10", "--max-seconds=30"])


``run_as_root``  

* Run the GuideLLM container as root user

