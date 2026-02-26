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

* default value: ``v0.5.3``


``timeout``  

* Timeout in seconds to wait for job completion

* default value: ``900``


``profile``  

* Guidellm profile to use

* default value: ``sweep``


``max_seconds``  

* Maximum seconds to run benchmark

* default value: ``30``


``processor``  

* Model processor name

* default value: ``RedHatAI/Meta-Llama-3.1-8B-Instruct-FP8-dynamic``


``data``  

* Data configuration

* default value: ``prompt_tokens=256,output_tokens=128``

