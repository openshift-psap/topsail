:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Rhods.update_datasciencecluster


rhods update_datasciencecluster
===============================

Update RHOAI datasciencecluster resource




Parameters
----------


``name``  

* Name of the resource to update. If none, update the first (and only) one found.


``enable``  

* List of all the components to enable
* type: List


``show_all``  

* If enabled, show all the available components and exit.


``extra_settings``  

* Dict of key:value to set manually in the DSC, using JSON dot notation.
* type: Dict

* default value: ``{'spec.components.kserve.serving.managementState': 'Removed'}``

