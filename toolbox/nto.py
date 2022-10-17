from toolbox._common import RunAnsibleRole, AnsibleRole

class NTO:
    """
    Commands for NTO related tasks
    """
    @AnsibleRole("nto_run_e2e_test")
    def run_e2e_test(
            self,
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

        return RunAnsibleRole(opts)
