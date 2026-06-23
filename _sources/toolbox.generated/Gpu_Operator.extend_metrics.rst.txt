:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Gpu_Operator.extend_metrics


gpu_operator extend_metrics
===========================

Enable time-sharing in the GPU Operator ClusterPolicy




Parameters
----------


``include_defaults``  

* If True, include the default DCGM metrics in the custom config

* default value: ``True``


``include_well_known``  

* If True, include well-known interesting DCGM metrics in the custom config


``namespace``  

* Namespace in which the GPU Operator is deployed

* default value: ``nvidia-gpu-operator``


``configmap_name``  

* Name of the ConfigMap where the configuration will be stored

* default value: ``metrics-config``


``extra_metrics``  

* If not None, a [{name,type,description}*] list of dictionnaries with the extra metrics to include in the custom config
* type: List


``wait_refresh``  

* If True, wait for the DCGM components to take into account the new configuration

* default value: ``True``

