:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Scheduler.deploy_mcad_from_helm


scheduler deploy_mcad_from_helm
===============================

Deploys MCAD from helm




Parameters
----------


``namespace``  

* Name of the namespace where MCAD should be deployed


``git_repo``  

* Name of the GIT repo to clone

* default value: ``https://github.com/project-codeflare/multi-cluster-app-dispatcher``


``git_ref``  

* Name of the GIT branch to fetch

* default value: ``main``


``image_repo``  

* Name of the image registry where the image is stored

* default value: ``quay.io/project-codeflare/mcad-controller``


``image_tag``  

* Tag of the image to use

* default value: ``stable``

