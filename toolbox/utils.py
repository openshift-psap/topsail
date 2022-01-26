import secrets

from toolbox._common import PlaybookRun


class Utils:
    """
    General-purpose command(s) independent of and usable by any tool
    """

    @staticmethod
    def build_push_image(
        image_name,
        quay_org_repo,
        auth_file,
        image_tag=None,
        dockerfile=None,
        git_repo=None,
        git_path=None,
        branch=None,
        memory=None
    ):
        """
        Build and publish an image to quay using either a Dockerfile or
        git repo.

        Args:
            image_name - Name of locally built image
            quay_org_repo - Org/Repo in quay to push to
            auth_file - Auth file for quay
            image_tag - Tag for image
            dockerfile - Path/Name of Dockerfile if used as source
            git_repo - Git repo containing Dockerfile if used as source
            git_path - Path to Dockerfile in git repo
            branch - Branch of repo to clone (default='main')
            memory - Required memory to build the image (in Gb)
        """

        if not image_tag:
            image_tag = secrets.token_hex(4)

        if memory:
            try:
                memory = str(float(memory)) + "Gi"
            except ValueError:
                print("ERROR: memory must be of type float or int")
                exit(1)

        if not git_repo and not dockerfile:
            print("Either a git repo or Dockerfile is required")
            exit(1)
        elif git_repo and dockerfile:
            print("Cannot have both a git repo and Dockerfile")
            exit(1)

        if git_repo and not git_path:
            print("Must supply a git path to Dockerfile within git repo")
            exit(1)

        opts = {
            "local_image_name": image_name,
            "image_tag": image_tag,
            "docker_path": dockerfile if dockerfile else "",
            "git_repo": git_repo if git_repo else "",
            "git_path": git_path if git_path else "",
            "branch": branch if branch else "main",
            "memory": memory if memory else "",
            "quay_repo": quay_org_repo,
            "auth_file": auth_file
        }

        return PlaybookRun("utils_build_push_image", opts)
