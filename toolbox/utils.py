import secrets

from toolbox._common import PlaybookRun


class Utils:
    """
    General-purpose command(s) independent of and usable by any tool
    """

    @staticmethod
    def build_push_image(
        image_name,
        image_tag=None,
        dockerfile=None,
        git_repo=None,
        git_path=None,
        quay_org_repo=None,
        auth_file=None
    ):
        """
        Build and publish an image to quay using either a Dockerfile or
        git repo. Will only publish if quay org/repo is specified (see
        args below for more details).

        Args:
            image_name - Name of locally built image
            image_tag - Tag for image
            dockerfile - Path/Name of Dockerfile if used as source
            git_repo - Git repo containing Dockerfile if used as source
            git_path - Path to Dockerfile in git repo
            quay_org_repo - Org/Repo in quay to push to
            auth_file - Auth file for quay
        """

        if not image_tag:
            image_tag = secrets.token_hex(4)

        opts = {
            "local_image_name": image_name,
            "image_tag": image_tag,
            "docker_path": dockerfile if dockerfile else "",
            "git_repo": git_repo if git_repo else "",
            "git_path": git_path if git_path else "",
            "quay_repo": quay_org_repo if quay_org_repo else "",
            "auth_file": auth_file if auth_file else ""
        }

        return PlaybookRun("utils_build_push_image", opts)
