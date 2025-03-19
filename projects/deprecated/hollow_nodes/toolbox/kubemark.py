import os
import sys

from projects.core.library.ansible_toolbox import (
    RunAnsibleRole, AnsibleRole,
    AnsibleMappedParams, AnsibleConstant,
    AnsibleSkipConfigGeneration
)

class Kubemark:
    """
    Commands relating to kubemark deployment
    """

    @AnsibleRole("kubemark_deploy_capi_provider")
    @AnsibleMappedParams
    def deploy_capi_provider(self):
        """
        Deploy the Kubemark Cluster-API provider

        Args:
        """

        return RunAnsibleRole(locals())


    @AnsibleRole("kubemark_deploy_nodes")
    @AnsibleMappedParams
    def deploy_nodes(self,
                     namespace="openshift-cluster-api",
                     deployment_name="kubemark-md",
                     count=4):
        """
        Deploy a set of Kubemark nodes

        Args:
          namespace: the namespace in which the MachineDeployment will be created
          deployment_name: the name of the MachineDeployment
          count: the number of nodes to deploy
        """

        return RunAnsibleRole(locals())
