import os
import sys

from projects.core.library.ansible_toolbox import (
    RunAnsibleRole, AnsibleRole,
    AnsibleMappedParams, AnsibleConstant,
    AnsibleSkipConfigGeneration
)

class Kwok:
    """
    Commands relating to KWOK deployment
    """

    @AnsibleRole("kwok_deploy_controller")
    @AnsibleMappedParams
    def deploy_kwok_controller(self, namespace="kube-system", undeploy=False):
        """
        Deploy the KWOK hollow node provider

        Args:
          namespace: namespace where KWOK will be deployed. Cannot be changed at the moment.
          undeploy: if true, undeploys KWOK instead of deploying it.
        """

        return RunAnsibleRole(locals())
