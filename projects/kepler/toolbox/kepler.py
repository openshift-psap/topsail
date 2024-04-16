from projects.core.library.ansible_toolbox import (
    RunAnsibleRole, AnsibleRole,
    AnsibleMappedParams, AnsibleConstant,
    AnsibleSkipConfigGeneration
)

class Kepler:
    """
    Commands relating to kepler deployment
    """

    @AnsibleRole("cluster_deploy_kepler")
    @AnsibleMappedParams
    def deploy_kepler(self):
        """
        Deploy the Kepler operator and monitor to track energy consumption

        Args:
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("cluster_undeploy_kepler")
    @AnsibleMappedParams
    def undeploy_kepler(self):
        """
        Cleanup the Kepler operator and associated resources

        Args:
        """

        return RunAnsibleRole(locals())
