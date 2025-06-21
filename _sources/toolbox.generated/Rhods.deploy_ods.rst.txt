:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Rhods.deploy_ods


rhods deploy_ods
================

Deploy ODS operator from its custom catalog




Parameters
----------


``catalog_image``  

* Container image containing the RHODS bundle.


``tag``  

* Catalog image tag to use to deploy RHODS.


``channel``  

* The channel to use for the deployment. Let empty to use the default channel.


``version``  

* The version to deploy. Let empty to install the last version available.


``disable_dsc_config``  

* If True, pass the flag to disable DSC configuration


``opendatahub``  

* If True, deploys a OpenDataHub manifest instead of RHOAI


``managed_rhoai``  

* If True, deploys RHOAI with the Managed Service flag. If False, deploys it as Self-Managed.

* default value: ``True``

