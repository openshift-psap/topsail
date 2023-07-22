import sys, os
import logging

from toolbox._common import RunAnsibleRole, AnsibleRole, AnsibleMappedParams


class Utils:
    """
    General-purpose command(s) independent of and usable by any tool
    """

    @AnsibleRole("utils_build_push_image")
    @AnsibleMappedParams
    def build_push_image(
            self,
            image_local_name,
            tag,
            namespace="ci-artifacts",
            remote_repo="",
            remote_auth_file="",
            git_repo="",
            git_ref="",
            dockerfile_path="Dockerfile",
            context_dir="/",
            memory: float = "",
            from_image = None,
            from_imagetag = None,
    ):
        """
        Build and publish an image to quay using either a Dockerfile or
        git repo.

        Args:
            image_local_name: Name of locally built image.
            tag: Tag for the image to build.
            namespace: Namespace where the local image will be built.
            remote_repo: Remote image repo to push to. If undefined, the image will not be pushed.
            remote_auth_file: Auth file for the remote repository.

            git_repo: Git repo containing Dockerfile if used as source. If undefined, the local path of 'dockerfile_path' will be used.
            git_ref: Git commit ref (branch, tag, commit hash) in the git repository.

            context_dir: Context dir inside the git repository.
            dockerfile_path: Path/Name of Dockerfile if used as source. If 'git_repo' is undefined, this path will be resolved locally, and the Dockerfile will be injected in the image BuildConfig.
            memory: Flag to specify the required memory to build the image (in Gb).
            from_image: Base image to use, instead of the FROM image specified in the Dockerfile.
            from_imagetag: Base imagestreamtag to use, instead of the FROM image specified in the Dockerfile.
        """

        if not git_repo and not dockerfile_path:
            logging.error("Either a git repo or a Dockerfile Path is required")
            sys.exit(1)

        both_or_none = lambda a, b: (a and b) or (not a and not b)

        if not both_or_none(remote_repo, remote_auth_file):
            logging.error("remote_repo and remote_auth_file must come together.")
            sys.exit(1)

        elif remote_repo:
            logging.info(f"Using remote repo {remote_repo} and auth file {remote_auth_file} to push the image.")
        else:
            logging.info(f"No remote repo provided, not pushing the image.")

        if not both_or_none(git_repo, git_ref):
            logging.error("git_repo and git_ref must come together.")
            sys.exit(1)

        elif git_repo:
            logging.info(f"Using Git repo {git_repo}|{git_ref}|{context_dir}|{dockerfile_path} for building the image.")
        else:
            logging.info(f"Using local dockerfile at {dockerfile_path} for building the image.")

        if not git_repo and context_dir != "/":
            logging.error("local builds (no git_repo) cannot specify a context_dir.")
            sys.exit(1)

        if memory:
            try:
                memory = str(float(memory))
                logging.info(f"Requesting {memory} of memory for building the image.")
            except ValueError:
                logging.error("memory must be of type float or int")
                sys.exit(1)

        if "/" in tag or "_" in tag:
            logging.error(f"the tag ('{tag}') cannot contain '/' or '_' characters")
            sys.exit(1)

        toolbox_name_suffix = os.environ.get("ARTIFACT_TOOLBOX_NAME_SUFFIX", "")
        # use `{image_local_name}_{tag}` as first suffix in the directory name
        os.environ["ARTIFACT_TOOLBOX_NAME_SUFFIX"] = f"_{image_local_name}_{tag}{toolbox_name_suffix}"

        del both_or_none

        if from_image and from_imagetag:
            logging.error(f"the --from-image={from_image} and --from-imagetag={from_imagetag} flags cannot be used at the same time.")
            sys.exit(1)            
        
        return RunAnsibleRole(locals())
