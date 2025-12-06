:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Storage.download_to_image


storage download_to_image
=========================

Downloads the a dataset into an image in the internal registry




Parameters
----------


``source``  

* URL of the source data


``image_name``  

* Name of the imagestream that will be create or used to store the dataset files.


``namespace``  

* Name of the namespace in which the imagestream will be created


``image_tag``  

* Tag to push the image with

* default value: ``latest``


``org_name``  

* Image will be pushed to <org_name>/<image_name>:<image_tag>

* default value: ``modelcars``


``creds``  

* Path to credentials to use for accessing the dataset.


``storage_dir``  

* Path to the data in the final image

* default value: ``/``


``base_image``  

* Base image for the image containing the data

* default value: ``registry.access.redhat.com/ubi9/ubi``

