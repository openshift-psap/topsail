import os
import sys
import logging

from projects.core.library.ansible_toolbox import (
    RunAnsibleRole, AnsibleRole,
    AnsibleMappedParams, AnsibleConstant,
    AnsibleSkipConfigGeneration
)

class Storage:
    """
    Commands relating to OpenShift file storage
    """

    @AnsibleRole("storage_deploy_aws_efs")
    @AnsibleMappedParams
    def deploy_aws_efs(self):
        """
        Deploy AWS EFS CSI driver and configure AWS accordingly.

        Assumes that AWS (credentials, Ansible module, Python module) is properly configured in the system.
        """

        return RunAnsibleRole()


    @AnsibleRole("storage_deploy_nfs_provisioner")
    @AnsibleMappedParams
    def deploy_nfs_provisioner(
            self,
            namespace="nfs-provisioner",
            pvc_sc=None, pvc_size="150Gi",
            storage_class_name="nfs-provisioner",
            default_sc=False
    ):
        """
        Deploy NFS Provisioner

        Args:
          namespace: The namespace where the resources will be deployed
          pvc_sc: The name of the storage class to use for the NFS-provisioner PVC
          pvc_size: The size of the PVC to give to the NFS-provisioner
          storage_class_name: The name of the storage class that will be created
          default_sc: Set to true to mark the storage class as default in the cluster
        """

        return RunAnsibleRole(locals())


    @AnsibleRole("storage_download_to_pvc")
    @AnsibleMappedParams
    def download_to_pvc(
            self,
            name,
            source,
            pvc_name,
            namespace,
            creds="",
            storage_dir="/",
            clean_first=False,
            pvc_access_mode="ReadWriteOnce",
            pvc_size="80Gi",
            pvc_storage_class_name=None,
            image="registry.access.redhat.com/ubi9/ubi",
    ):
        """
        Downloads the a dataset into a PVC of the cluster

        Args:
            name: Name of the data source
            source: URL of the source data
            pvc_name: Name of the PVC that will be create to store the dataset files.
            namespace: Name of the namespace in which the PVC will be created
            creds: Path to credentials to use for accessing the dataset.
            clean_first: if True, clears the storage directory before downloading.
            storage_dir: the path where to store the downloaded files, in the PVC
            pvc_access_mode: the access mode to request when creating the PVC
            pvc_size: the size of the PVC to request, when creating the PVC
            pvc_storage_class_name: the name of the storage class to pass when creating the PVC
            image: the image to use for running the download Pod
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("storage_download_to_image")
    @AnsibleMappedParams
    def download_to_image(
            self,
            source,
            image_name,
            namespace,
            image_tag="latest",
            org_name="modelcars",
            creds="",
            storage_dir="/",
            base_image="registry.access.redhat.com/ubi9/ubi",
    ):
        """
        Downloads the a dataset into an image in the internal registry

        Args:
            source: URL of the source data
            image_name: Name of the imagestream that will be create or used to store the dataset files.
            namespace: Name of the namespace in which the imagestream will be created
            image_tag: tag to push the image with
            org_name: image will be pushed to <org_name>/<image_name>:<image_tag>
            creds: Path to credentials to use for accessing the dataset.
            storage_dir: path to the data in the final image
            base_image: base image for the image containing the data
        """

        return RunAnsibleRole(locals())
