import sys

from toolbox._common import RunAnsibleRole, AnsibleRole, AnsibleMappedParams, AnsibleConstant, AnsibleSkipConfigGeneration


class Pipelines:
    """
    Commands relating to RHODS
    """

    @AnsibleRole("pipelines_deploy_application")
    @AnsibleMappedParams
    def deploy_application(self, name, namespace):
        """
        Deploy a Data Science Pipeline Application in a given namespace.

        Args:
          name: the name of the application to deploy
          namespace: the namespace in which the application should be deployed
        """

        return RunAnsibleRole(locals())
