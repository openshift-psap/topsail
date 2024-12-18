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
    def prepare_topsail(
            self,
            cluster_lock,
            pr_number=None,
            repo_owner="openshift-psap",
            repo_name="topsail",
            image_name="localhost/topsail",
            image_tag=None,
            dockerfile_name="build/Dockerfile",
            cleanup_old_pr_images=True,
    ):
        """
        Prepares the jump host for running TOPSAIL:
        - clones TOPSAIL repository
        - builds TOPSAIL image in the remote host

        Args:
          cluster_lock: Name of the cluster lock to use
          pr_number: PR number to use for the test. If none, use the main branch.

          repo_owner: Name of the Github repo owner
          repo_name: Name of the TOPSAIL github repo
          image_name: Name to use when building TOPSAIL image
          image_tag: Name to give to the tag, or computed if empty
          dockerfile_name: Name/path of the Dockerfile to use to build the image
          cleanup_old_pr_images: if disabled, don't cleanup the old images
        """

        return RunAnsibleRole(locals())
