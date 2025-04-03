:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Mac_Ai.remote_ramalama_run_model


mac_ai remote_ramalama_run_model
================================

Runs a model with ramalama, on a remote host




Parameters
----------


``base_work_dir``  

* The base directory where to store things


``path``  

* The path to the llama-server binary


``port``  

* The port number on which llama-cpp should listen


``model_name``  

* The name of the model to run


``env``  

* The env values to set before running ramalama


``ngl``  

* Number of layers to store in VRAM

* default value: ``99``


``device``  

* Name of the device to pass to the container


``unload``  

* If True, unloads (stops serving) this model


``image``  

* The image to use to run ramalama

* default value: ``quay.io/ramalama/ramalama:latest``

