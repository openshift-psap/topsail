:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Gpu_Operator.deploy_from_operatorhub


gpu_operator deploy_from_operatorhub
====================================

Deploys the GPU operator from OperatorHub




Parameters
----------


``namespace``  

* Optional namespace in which the GPU Operator will be deployed. Before v1.9, the value must be "openshift-operators". With >=v1.9, the namespace can freely chosen. Default: nvidia-gpu-operator.

* default value: ``nvidia-gpu-operator``


``version``  

* Optional version to deploy. If unspecified, deploys the latest version available in the selected channel. Run the toolbox gpu_operator list_version_from_operator_hub subcommand to see the available versions.


``channel``  

* Optional channel to deploy from. If unspecified, deploys the CSV's default channel.


``installPlan``  

* Optional InstallPlan approval mode (Automatic or Manual [default])

* default value: ``Manual``

