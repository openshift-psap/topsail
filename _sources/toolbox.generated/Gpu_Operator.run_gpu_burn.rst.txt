:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Gpu_Operator.run_gpu_burn


gpu_operator run_gpu_burn
=========================

Runs the GPU burn on the cluster




Parameters
----------


``namespace``  

* Namespace in which GPU-burn will be executed

* default value: ``default``


``runtime``  

* How long to run the GPU for, in seconds
* type: Int

* default value: ``30``


``keep_resources``  

* If true, do not delete the GPU-burn ConfigMaps
* type: Bool


``ensure_has_gpu``  

* If true, fails if no GPU is available in the cluster.
* type: Bool

* default value: ``True``

