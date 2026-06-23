:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Crc.refresh_image


crc refresh_image
=================

Update a CRC AMI image with a given SNC repo commit




Parameters
----------


``source_snapshot_id``  

* The source Snapshot ID (e.g., snap-0123...)


``new_ami_name``  

* The name for the new AMI


``key_pair_name``  

* An existing EC2 Key Pair name for the worker instance


``private_key_path``  

* Path to the private key to use to login into the controller EC2


``git_repo``  

* The URL of the repo to use for updating the SNC image


``git_branch``  

* The repo branch to use for updating the SNC image


``script``  

* Name of the local script to execute (update_disk or refresh_image)

* default value: ``refresh_image``


``disk_size``  

* Size of the spare disk. Optional.


``aws_region``  

* The region to use

* default value: ``us-west-1``


``aws_availability_zone``  

* The availability zone to use

* default value: ``us-west-1a``


``worker_instance_type``  

* The instance type for the controller EC2

* default value: ``t2.micro``


``worker_ami_id``  

* The AMI ID to run on the controller EC2

* default value: ``ami-0020037e76c9ad658``


``security_group_name``  

* The name of the security-group to use. Date will be added

* default value: ``topsail-refresh-image-sg``


``ami_image_user``  

* The name of the user to use in the image

* default value: ``fedora``

