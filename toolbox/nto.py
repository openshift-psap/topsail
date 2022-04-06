from toolbox._common import RunAnsibleRole

class NTO:
    """
    Commands for NTO related tasks
    """
    @staticmethod
    def run_e2e_test(
            git_repo,
            git_ref,
    ):
        """
        Run NTO e2e tests

        Args:
            git_repo: Git repository URL where to find the e2e tests
            git_ref: Git reference to clone
        """
        opts = {
            "nto_git_repo": git_repo,
            "nto_git_ref": git_ref,
        }

        return RunAnsibleRole("nto_run_e2e_test", opts)
