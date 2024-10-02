:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: repo generate_toolbox_rst_documentation
    _ Source component: Cluster.build_push_image


cluster build_push_image
========================

Build and publish an image to quay using either a Dockerfile or git repo.




Parameters
----------


``image_local_name``  

* Name of locally built image.


``tag``  

* Tag for the image to build.


``namespace``  

* Namespace where the local image will be built.


``remote_repo``  

* Remote image repo to push to. If undefined, the image will not be pushed.


``remote_auth_file``  

* Auth file for the remote repository.


``git_repo``  

* Git repo containing Dockerfile if used as source. If undefined, the local path of 'dockerfile_path' will be used.


``git_ref``  

* Git commit ref (branch, tag, commit hash) in the git repository.


``dockerfile_path``  

* Path/Name of Dockerfile if used as source. If 'git_repo' is undefined, this path will be resolved locally, and the Dockerfile will be injected in the image BuildConfig.

* default value: ``Dockerfile``


``context_dir``  

* Context dir inside the git repository.

* default value: ``/``


``memory``  

* Flag to specify the required memory to build the image (in Gb).
* type: Float


``from_image``  

* Base image to use, instead of the FROM image specified in the Dockerfile.


``from_imagetag``  

* Base imagestreamtag to use, instead of the FROM image specified in the Dockerfile.

