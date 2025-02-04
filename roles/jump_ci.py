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
    def take_lock(self, cluster, owner):
        """
        Take a lock with a given cluster name on a remote node

        Args:
          cluster: name of the cluster lock to take
          owner: name of the lock owner
        """

        if not cluster: # don't accept the empty string value
            raise ValueError("--cluster must be set")

        return RunAnsibleRole(locals())


    @AnsibleRole("jump_ci_ensure_lock")
    @AnsibleMappedParams
    def ensure_lock(self, cluster, owner, check_kubeconfig=True):
        """
        Ensure that cluster lock with a given name is taken. Fails otherwise.

        Args:
          cluster: name of the cluster lock to test
          owner: name of the lock owner
          check_kubeconfig: if enabled, ensure that the cluster's kubeconfig file exists
        """

        if not cluster: # don't accept the empty string value
            raise ValueError("--cluster must be set")

        return RunAnsibleRole(locals())

    @AnsibleRole("jump_ci_release_lock")
    @AnsibleMappedParams
    def release_lock(self, cluster, owner):
        """
        Release a cluster lock with a given name on a remote node

        Args:
          cluster: name of the cluster lock to release
          owner: name of the lock owner
        """

        if not cluster: # don't accept the empty string value
            raise ValueError("--cluster must be set")

        return RunAnsibleRole(locals())


    @AnsibleRole("jump_ci_prepare_topsail")
    @AnsibleMappedParams
    def prepare_topsail(
            self,
            cluster,
            lock_owner,
            pr_number=None,
            repo_owner="openshift-psap",
            repo_name="topsail",
            git_ref=None,
            image_name="localhost/topsail",
            image_tag=None,
            dockerfile_name="build/Dockerfile",
            update_from_imagetag="main",
            cleanup_old_pr_images=True,
    ):
        """
        Prepares the jump host for running TOPSAIL:
        - clones TOPSAIL repository
        - builds TOPSAIL image in the remote host

        Args:
          cluster: Name of the cluster to use
          lock_owner: name of the lock owner
          pr_number: PR number to use for the test. If none, use the main branch.

          repo_owner: Name of the Github repo owner
          repo_name: Name of the TOPSAIL github repo
          git_ref: the ref (commit/branch) to use in the git repository. Use the PR's `/merge` if not specify, or the main branch if no PR number is specified.
          image_name: Name to use when building TOPSAIL image
          image_tag: Name to give to the tag, or computed if empty
          dockerfile_name: Name/path of the Dockerfile to use to build the image
          cleanup_old_pr_images: if disabled, don't cleanup the old images
          update_from_imagetag: if set, update the git tree from this image instead of building from scratch
        """

        if not cluster: # don't accept the empty string value
            raise ValueError("--cluster must be set")

        return RunAnsibleRole(locals())

    @AnsibleRole("jump_ci_prepare_step")
    @AnsibleMappedParams
    def prepare_step(
            self,
            cluster,
            lock_owner,
            project,
            step,
            env_file,
            variables_overrides_dict,
            secrets_path_env_key=None,
    ):
        """
        Prepares the jump host for running a CI test step:

        Args:
          cluster: Name of the cluster lock to use
          lock_owner: name of the lock owner
          project: Name of the project to execute
          step: Name of the step to execute
          env_file: Path to the env file to use
          variables_overrides_dict: Dictionnary to save as the variable overrides file
          secrets_path_env_key: If provided, the env key will be used to locate the secret directories to upload to the jump host
        """

        if not cluster: # don't accept the empty string value
            raise ValueError("--cluster must be set")

        return RunAnsibleRole(locals())

    @AnsibleRole("jump_ci_retrieve_artifacts")
    @AnsibleMappedParams
    def retrieve_artifacts(
            self,
            cluster,
            lock_owner,
            remote_dir,
            local_dir="artifacts",
            skip_cluster_lock=False
    ):
        """
        Prepares the jump host for running a CI test step:

        Args:
          cluster: Name of the cluster lock to use
          lock_owner: name of the lock owner
          remote_dir: name of remote directory to retrieve.
          local_dir: name of the local dir where to store the results, within the extra logs artifacts directory.
          skip_cluster_lock: if True, skip the cluster is lock check (eg, when included from another role).
        """

        if not cluster: # don't accept the empty string value
            raise ValueError("--cluster must be set")

        return RunAnsibleRole(locals())
