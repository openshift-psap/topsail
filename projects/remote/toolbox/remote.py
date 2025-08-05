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
            version=None,
            refspec=None,
            force=False
    ):
        """
        Clones a Github repository in a remote host

        Args:
          repo_url: the URL of the repo to clone
          dest: the directory where the repo should be cloned
          version: the git version to clone
          refspec: the git ref to clone. Can't be set with version
          force: force the git clone
        """

        if version and refspec:
            raise ValueError(f"--version={version} and --refspec={refspec} can't be pass together")

        return RunAnsibleRole(locals())

    @AnsibleRole("remote_download")
    @AnsibleMappedParams
    def download(
            self,
            source,
            dest,
            force=False,
            executable=False,
            tarball=False,
            zip=False,
    ):
        """
        Downloads a file in a remote host

        Args:
          source: the URL of the file to download
          dest: the location where to save the file
          force: force the download
          executable: if true, make the file executable
          tarball: if true, untar the tarball
          zip: if true, unzip the zipball (currently only on MacOS)
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("remote_retrieve")
    @AnsibleMappedParams
    def retrieve(
            self,
            path,
            dest,
            push_mode=False,
    ):
        """
        Retrieves remote files locally

        Args:
          path: the location of the files in the remote system
          dest: the location where to save the files
          push_mode: if enabled, push to the remote system instead of pulling
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("remote_build_image")
    @AnsibleMappedParams
    def build_image(
            self,
            base_directory,
            container_file,
            image,
            podman_cmd="podman",
            prepare_script=None,
            container_file_is_local=False,
            build_args={},
    ):
        """
        Builds a podman image

        Args:
          base_directory: the location of the directory to build. If None, uses an empty temp dir
          container_file: the path the container_file to build
          image: the name of the image to build
          podman_cmd: the command to invoke to run podman
          prepare_script: if specified, a script to execute before building the image
          container_file_is_local: if true, copy the containerfile from the local system
          build_args: dict of build args kv to pass to podman build.
        """

        if container_file_is_local and base_directory:
            raise ValueError("Cannot have a --base_directory when --container_file_is_local is set")

        return RunAnsibleRole(locals())
