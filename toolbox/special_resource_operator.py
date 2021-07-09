from toolbox._common import PlaybookRun


class SpecialResourceOperator:
    """
    Commands for deploying, building and testing the Special Resource Operator in various ways
    """
    @staticmethod
    def capture_deployment_state():
        return PlaybookRun("sro_capture_deployment_state")

    @staticmethod
    def deploy_from_commit(git_repo, git_ref, image_tag=None):
        """
        Deploys the SRO operator from the given git commit

        Args:
            git_repo: The git repository to deploy from, e.g. https://github.com/openshift-psap/special-resource-operator.git
            git_ref: The git ref to deploy from, e.g. master
            image_tag: The SRO operator image tag UID.
        """
        opts = {
            "sro_git_repo": git_repo,
            "sro_git_ref": git_ref,
        }

        if image_tag is not None:
            opts["sro_image_tag"] = image_tag

        return PlaybookRun("sro_deploy_custom_commit", opts)

    @staticmethod
    def run_e2e_test(git_repo, git_ref):
        """
        Runs e2e test on the given SRO repo and ref

        Args:
            git_repo: The git repository to deploy from, e.g. https://github.com/openshift-psap/special-resource-operator.git
            git_ref: The git ref to deploy from, e.g. master
        """
        opts = {
            "sro_git_repo": git_repo,
            "sro_git_ref": git_ref,
        }

        return PlaybookRun("sro_run_e2e_test", opts)

    @staticmethod
    def undeploy_from_commit(git_repo, git_ref):
        """
        Undeploys an SRO-operator that was deployed from commit

        Args:
            git_repo: The git repository to undeploy, e.g. https://github.com/openshift-psap/special-resource-operator.git
            git_ref: The git ref to undeploy, e.g. master
        """
        opts = {
            "sro_git_repo": git_repo,
            "sro_git_ref": git_ref,
        }

        return PlaybookRun("sro_undeploy_custom_commit", opts)
