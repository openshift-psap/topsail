:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Mac_Ai.remote_llama_cpp_run_bench


mac_ai remote_llama_cpp_run_bench
=================================

Benchmark a model with llama_cpp, on a remote host




Parameters
----------


``path``  

* The path to the llama.cpp bin directory


``model_name``  

* The name of the model to use


``prefix``  

* The prefix to get the llama.cpp binaries running


``ngl``  

* Number of layers to store in VRAM

* default value: ``99``


``verbose``  

* If true, runs the benchmark in verbose mode

* default value: ``True``


``llama_bench``  

* If true, runs the llama-bench benchmark

* default value: ``True``


``test_backend_ops``  

* If true, runs the test-backend-ops benchmark

* default value: ``True``

