:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Storage.download_to_pvc


storage download_to_pvc
=======================

Downloads the a dataset into a PVC of the cluster




Parameters
----------


``name``  

* Name of the data source


``source``  

* URL of the source data


``pvc_name``  

* Name of the PVC that will be create to store the dataset files.


``namespace``  

* Name of the namespace in which the PVC will be created


``creds``  

* Path to credentials to use for accessing the dataset.


``storage_dir``  

* The path where to store the downloaded files, in the PVC

* default value: ``/``


``clean_first``  

* If True, clears the storage directory before downloading.


``pvc_access_mode``  

* The access mode to request when creating the PVC

* default value: ``ReadWriteOnce``


``pvc_size``  

* The size of the PVC to request, when creating the PVC

* default value: ``80Gi``


``pvc_storage_class_name``  

* The name of the storage class to pass when creating the PVC


``image``  

* The image to use for running the download Pod

* default value: ``registry.access.redhat.com/ubi9/ubi``

