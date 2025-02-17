:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Remote.build_image


remote build_image
==================

Builds a podman image




Parameters
----------


``base_directory``  

* The location of the directory to build


``container_file``  

* The path the container_file to build


``image``  

* The name of the image to build


``force``  

* Force build the image even if it already exists


``podman_cmd``  

* The command to invoke to run podman

* default value: ``podman``


``prepare_script``  

* If specified, a script to execute before building the image

