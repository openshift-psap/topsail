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


    @AnsibleRole("kwok_set_scale")
    @AnsibleMappedParams
    def set_scale(
            self,
            scale,
            taint=None,
            name="kwok-machine",
            role="worker",
            cpu=32,
            memory=256,
            gpu=None,
            pods=250,
    ):
        """
        Deploy a set of KWOK nodes

        Args:
          scale: The number of required nodes with given instance type
          taint: Taint to apply to the machineset.
          name: Name to give to the new machineset.
          role: Role of the new nodes

          cpu: number of CPU allocatable
          memory: number of Gi of memory allocatable
          gpu: number of nvidia.com/gpu allocatable
          pods: number of Pods allocatable
        """

        return RunAnsibleRole(locals())
