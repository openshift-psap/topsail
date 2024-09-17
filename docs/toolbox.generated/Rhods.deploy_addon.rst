:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Rhods.deploy_addon


rhods deploy_addon
==================

Installs the RHODS OCM addon




Parameters
----------


``cluster_name``  

* The name of the cluster where RHODS should be deployed.


``notification_email``  

* The email to register for RHODS addon deployment.


``wait_for_ready_state``  

* If true (default), will cause the role to wait until addon reports ready state. (Can time out)

* default value: ``True``


# Constants
# Identifier of the addon that should be deployed
# Defined as a constant in Rhods.deploy_addon
ocm_deploy_addon_ocm_deploy_addon_id: managed-odh
