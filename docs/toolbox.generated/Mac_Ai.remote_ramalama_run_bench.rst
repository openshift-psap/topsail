:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Mac_Ai.remote_ramalama_run_bench


mac_ai remote_ramalama_run_bench
================================

Benchmark a model with ramalama, on a remote host




Parameters
----------


``base_work_dir``  

* The base directory where to store things


``path``  

* The path to the llama.cpp bin directory


``model_name``  

* The name of the model to use


``env``  

* The env values to set before running ramalama


``ngl``  

* Number of layers to store in VRAM

* default value: ``99``


``device``  

* Name of the device to pass to the container


``image``  

* The image to use to run ramalama

* default value: ``quay.io/ramalama/ramalama:latest``

