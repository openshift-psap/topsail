:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Gpu_Operator.enable_time_sharing


gpu_operator enable_time_sharing
================================

Enable time-sharing in the GPU Operator ClusterPolicy




Parameters
----------


``replicas``  

* Number of slices available for each of the GPUs


``namespace``  

* Namespace in which the GPU Operator is deployed

* default value: ``nvidia-gpu-operator``


``configmap_name``  

* Name of the ConfigMap where the configuration will be stored

* default value: ``time-slicing-config-all``

