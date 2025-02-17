import sys

from projects.core.library.ansible_toolbox import (
    RunAnsibleRole, AnsibleRole,
    AnsibleMappedParams, AnsibleConstant,
    AnsibleSkipConfigGeneration
)

class Remote:
    """
    Commands relating to the setup of remote hosts
    """

    @AnsibleRole("remote_clone")
    @AnsibleMappedParams
    def clone(
            self,
            repo_url,
            dest,
            version="main",
            force=False
    ):
        """
        Clones a Github repository in a remote host

        Args:
          repo_url: the URL of the repo to clone
          dest: the directory where the repo should be cloned
          version: the git version to clone
          force: force the git clone
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("remote_download")
    @AnsibleMappedParams
    def download(
            self,
            source,
            dest,
            force=False,
            executable=False,
            tarball=True,
    ):
        """
        Downloads a file in a remote host

        Args:
          source: the URL of the file to download
          dest: the location where to save the file
          force: force the download
          executable: if true, make the file executable
          tarball: if true, untar the tarball
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("remote_retrieve")
    @AnsibleMappedParams
    def retrieve(
            self,
            path,
            dest,
    ):
        """
        Retrieves remote files locally

        Args:
          path: the location of the files in the remote system
          dest: the location where to save the files
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("remote_build_image")
    @AnsibleMappedParams
    def build_image(
            self,
            base_directory,
            container_file,
            image,
            force=False,
            podman_cmd="podman",
            prepare_script=None,
    ):
        """
        Builds a podman image

        Args:
          base_directory: the location of the directory to build
          container_file: the path the container_file to build
          image: the name of the image to build
          force: force build the image even if it already exists
          podman_cmd: the command to invoke to run podman
          prepare_script: if specified, a script to execute before building the image
        """

        return RunAnsibleRole(locals())
