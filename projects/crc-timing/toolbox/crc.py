import os
import sys
import logging

from projects.core.library.ansible_toolbox import (
    RunAnsibleRole, AnsibleRole,
    AnsibleMappedParams, AnsibleConstant,
    AnsibleSkipConfigGeneration
)

class Crc:
    """
    Commands relating to CRC
    """

    @AnsibleRole("crc_timing_refresh_image")
    @AnsibleMappedParams
    def refresh_image(
            self,
            source_snapshot_id,
            new_ami_name,
            key_pair_name,
            private_key_path,
            git_repo,
            git_branch,
            aws_region="us-west-1",
            aws_availability_zone="us-west-1a",
            worker_instance_type="t2.micro",
            worker_ami_id="ami-0020037e76c9ad658", # Fedora-Cloud-Base-AmazonEC2.x86_64-42-Prerelease-202504
            security_group_name="topsail-refresh-image-sg",
            ami_image_user="fedora",
    ):
        """
        Update a CRC AMI image with a given SNC repo commit

        Args:
            source_snapshot_id: the source Snapshot ID (e.g., snap-0123...)
            new_ami_name: the name for the new AMI
            key_pair_name: an existing EC2 Key Pair name for the worker instance
            private_key_path: path to the private key to use to login into the controller EC2
            git_repo: the URL of the repo to use for updating the SNC image
            git_branch: the repo branch to use for updating the SNC image

            aws_region: the region to use
            aws_availability_zone: the availability zone to use
            worker_instance_type: the instance type for the controller EC2
            worker_ami_id: the AMI ID to run on the controller EC2
            security_group_name: the name of the security-group to use. Date will be added
            ami_image_user: the name of the user to use in the image
        """

        return RunAnsibleRole(locals())
