import datetime
import logging
import sys

from projects.core.library.ansible_toolbox import (
    RunAnsibleRole, AnsibleRole,
    AnsibleMappedParams, AnsibleConstant,
    AnsibleSkipConfigGeneration
)

class Jump_Ci:
    """
    Commands to run TOPSAIL scripts in a jump host
    """

    @AnsibleRole("jump_ci_take_lock")
    @AnsibleMappedParams
    def take_lock(self, cluster):
        """
        Take a lock with a given cluster name on a remote node

        Args:
          cluster: name of the cluster lock to take
        """

        return RunAnsibleRole(locals())


    @AnsibleRole("jump_ci_ensure_lock")
    @AnsibleMappedParams
    def ensure_lock(self, cluster):
        """
        Ensure that cluster lock with a given name is taken. Fails otherwise.

        Args:
          cluster: name of the cluster lock to test
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("jump_ci_release_lock")
    @AnsibleMappedParams
    def release_lock(self, cluster):
        """
        Release a cluster lock with a given name on a remote node

        Args:
          cluster: name of the cluster lock to release
        """

        return RunAnsibleRole(locals())


    @AnsibleRole("jump_ci_prepare_topsail")
    @AnsibleMappedParams
    def prepare_topsail(self):
        """
        Prepares the jump host for running TOPSAIL

        Args:
          pass
        """

        return RunAnsibleRole(locals())
