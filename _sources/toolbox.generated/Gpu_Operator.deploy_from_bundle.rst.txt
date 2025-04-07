:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Gpu_Operator.deploy_from_bundle


gpu_operator deploy_from_bundle
===============================

Deploys the GPU Operator from a bundle




Parameters
----------


``bundle``  

* Either a bundle OCI image or "master" to deploy the latest bundle


``namespace``  

* Optional namespace in which the GPU Operator will be deployed. Before v1.9, the value must be "openshift-operators". With >=v1.9, the namespace can freely chosen (except 'openshift-operators'). Default: nvidia-gpu-operator.

* default value: ``nvidia-gpu-operator``

