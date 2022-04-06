import sys

import secrets

from toolbox._common import RunAnsibleRole


class Utils:
    """
    General-purpose command(s) independent of and usable by any tool
    """

    @staticmethod
    def build_push_image(
        local_image_name,
        image_tag="",
        namespace="ci-artifacts",
        remote_repo="",
        remote_auth_file="",
        git_repo="",
        git_ref="",
        dockerfile_path="Dockerfile",
        context_dir="/",
        memory=""
    ):
        """
        Build and publish an image to quay using either a Dockerfile or
        git repo.

        Args:
            local_image_name: Name of locally built image.
            image_tag: Optional tag for the image to build. If undefined, a random tag will be generated.
            namespace: Optional namespace where the local image will be built. Default: ci-artifacts.
            remote_repo: Optional remote image repo to push to. If undefined, the image will not be pushed.
            remote_auth_file: Optional auth file for the remote repository.

            git_repo: Optional Git repo containing Dockerfile if used as source. If undefined, the local path of 'dockerfile_path' will be used.
            git_ref: Optional Git commit ref (branch, tag, commit hash) in the git repository.

            context_dir: Optional context dir inside the git repository. Default /.
            dockerfile_path: Optional Path/Name of Dockerfile if used as source. Default: Dockerfile. If 'git_repo' is undefined, this path will be resolved locally, and the Dockerfile will be injected in the image BuildConfig.
            memory: Optional flag to specify the required memory to build the image (in Gb).
        """

        if not git_repo and not dockerfile_path:
            print("Either a git repo or a Dockerfile Path is required")
            sys.exit(1)

        both_or_none = lambda a, b: (a and b) or (not a and not b)

        if not both_or_none(remote_repo, remote_auth_file):
            print("ERROR: remote_repo and remote_auth_file must come together.")
            sys.exit(1)
        elif remote_repo:
            print(f"Using remote repo {remote_repo} and auth file {remote_auth_file} to push the image.")
        else:
            print(f"No remote repo provided, not pushing the image.")

        if not both_or_none(git_repo, git_ref):
            print("ERROR: git_repo and git_ref must come together.")
            sys.exit(1)
        elif git_repo:
            print(f"Using Git repo {git_repo}|{git_ref}|{context_dir}|{dockerfile_path} for building the image.")
        else:
            print(f"Using local dockerfile at {dockerfile_path} for building the image.")

        if not git_repo and context_dir != "/":
            print("ERROR: local builds (no git_repo) cannot specify a context_dir.")
            sys.exit(1)

        if memory:
            try:
                memory = str(float(memory)) + "Gi"
            except ValueError:
                print("ERROR: memory must be of type float or int")
                sys.exit(1)
            print(f"Requesting {memory} of memory for building the image.")

        if not image_tag:
            image_tag = secrets.token_hex(4)
            print(f"Using '{image_tag}' as image tag.")

        opts = {
            "utils_build_push_image_local_name": local_image_name,
            "utils_build_push_image_tag": image_tag,
            "utils_build_push_image_namespace": namespace,

            "utils_build_push_image_remote_repo": remote_repo,
            "utils_build_push_image_remote_auth_file": remote_auth_file,

            "utils_build_push_image_git_repo": git_repo,
            "utils_build_push_image_git_ref": git_ref,

            "utils_build_push_image_context_dir": context_dir,
            "utils_build_push_image_dockerfile_path": dockerfile_path,

            "utils_build_push_image_memory": memory,
        }

        return RunAnsibleRole("utils_build_push_image", opts)
