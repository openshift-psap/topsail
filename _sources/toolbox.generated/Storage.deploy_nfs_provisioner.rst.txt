:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Storage.deploy_nfs_provisioner


storage deploy_nfs_provisioner
==============================

Deploy NFS Provisioner




Parameters
----------


``namespace``  

* The namespace where the resources will be deployed

* default value: ``nfs-provisioner``


``pvc_sc``  

* The name of the storage class to use for the NFS-provisioner PVC

* default value: ``gp3-csi``


``pvc_size``  

* The size of the PVC to give to the NFS-provisioner

* default value: ``10Gi``


``storage_class_name``  

* The name of the storage class that will be created

* default value: ``nfs-provisioner``


``default_sc``  

* Set to true to mark the storage class as default in the cluster

