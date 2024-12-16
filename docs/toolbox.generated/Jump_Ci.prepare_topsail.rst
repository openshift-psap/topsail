:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Jump_Ci.prepare_topsail


jump_ci prepare_topsail
=======================

Prepares the jump host for running TOPSAIL: - clones TOPSAIL repository - builds TOPSAIL image in the remote host




Parameters
----------


``cluster_lock``  

* Name of the cluster lock to use


``pr_number``  

* PR number to use for the test. If none, use the main branch.


``repo_owner``  

* Name of the Github repo owner

* default value: ``openshift-psap``


``repo_name``  

* Name of the TOPSAIL github repo

* default value: ``topsail``


``image_name``  

* Name to use when building TOPSAIL image

* default value: ``localhost/topsail``


``image_tag``  

* Name to give to the tag, or computed if empty


``dockerfile_name``  

* Name/path of the Dockerfile to use to build the image

* default value: ``build/Dockerfile``


``cleanup_old_pr_images``  

* If disabled, don't cleanup the old images

* default value: ``True``

