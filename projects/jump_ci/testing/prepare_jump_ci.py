import os
import logging
import json

from projects.core.library import env, config, run
from projects.jump_ci.testing import utils, tunnelling

@utils.entrypoint()
def lock_cluster(cluster=None):
    """
    Take the lock on a given cluster

    Args:
      cluster: Name of the cluster lock to use
    """
    if os.environ.get("OPENSHIFT_CI") == "true":
        config.project.set_config("ssh_tunnel.enabled", "true")

        if config.project.get_config("cluster.name", print=False) is None:
            override_cluster = config.project.get_config("overrides.PR_POSITIONAL_ARG_1", None)
            if not override_cluster:
                raise ValueError("Expected to find the cluster name in overrides.PR_POSITIONAL_ARG_1 (1st test argument) or cluster.name, but none of them were set ...")

            config.project.set_config("cluster.name", override_cluster)
            config.project.set_config("rewrite_variables_overrides.cluster_found_in_pr_args", True)


    if cluster is None:
        cluster = config.project.get_config("cluster.name")

    # Open the tunnel
    tunnelling.prepare()

    run.run_toolbox("jump_ci", "take_lock", cluster=cluster, owner=utils.get_lock_owner())



@utils.entrypoint()
def unlock_cluster(cluster=None):
    """
    Release the lock on a given cluster

    Args:
      cluster: Name of the cluster lock to use
    """
    # Open the tunnel
    tunnelling.prepare()

    if cluster is None:
        cluster = config.project.get_config("cluster.name")

    run.run_toolbox("jump_ci", "release_lock", cluster=cluster, owner=utils.get_lock_owner())


@utils.entrypoint()
def prepare(
        cluster=None,
        repo_owner="openshift-psap",
        repo_name="topsail",
        git_ref=None,
        pr_number=None,
):
    """
    Prepares the jump-host for running TOPSAIL commands.
    Args:
      cluster: Name of the cluster to use
      owner: Name of the Github repo owner
      repo: Name of the TOPSAIL github repo
      git_ref: Commit to use in the TOPSAIL repo
      pr_number: PR number to use for the test. If none, use the main branch.
    """

    # Open the tunnel
    tunnelling.prepare()

    if cluster is None:
        cluster = config.project.get_config("cluster.name")

    # Lock the cluster
    run.run_toolbox("jump_ci", "ensure_lock", cluster=cluster, owner=utils.get_lock_owner())

    # Clone the Git Repository
    # Build the image
    prepare_topsail_args = dict(
        cluster=cluster,
        lock_owner=utils.get_lock_owner(),
    )

    if os.environ.get("OPENSHIFT_CI") == "true":
        if os.environ.get("OPENSHIFT_CI_TOPSAIL_FOREIGN_TESTING"):
            logging.info("Not running from TOPSAIL repository. Using TOPSAIL foreign configuration.")
            repo_owner = config.project.get_config("foreign_testing.topsail.repo.owner")
            repo_name = config.project.get_config("foreign_testing.topsail.repo.name")
            git_ref  = config.project.get_config("foreign_testing.topsail.repo.branch")

        elif os.environ["JOB_NAME"].startswith("periodic"):
            # periodic jobs don't have these env vars ...
            job_spec = job_spec = json.loads(os.environ["JOB_SPEC"])
            repo_owner = os.environ["REPO_OWNER"] = job_spec["extra_refs"][0]["org"]
            repo_name = os.environ["REPO_NAME"] = job_spec["extra_refs"][0]["repo"]
            git_ref = os.environ["PULL_PULL_SHA"] = job_spec["extra_refs"][0]["base_ref"]

        prepare_topsail_args |= dict(
            repo_owner=repo_owner,
            repo_name=repo_name,
            git_ref=git_ref,
            pr_number=os.environ.get("PULL_NUMBER"),
        )
    elif any([pr_number, git_ref]):
        if not all([repo_owner, repo_name, pr_number]):
            logging.fatal("Missing parameters in the CLI arguments. Please pass at least --pr-number")
            raise SystemExit(1)

        prepare_topsail_args |= dict(
            repo_owner=repo_owner,
            repo_name=repo_name,
            pr_number=pr_number,
            git_ref=git_ref,
        )

    else:
        logging.fatal("No flag provided and couldn't determine the CI environment ... Aborting.")
        logging.info("Outside of the CI, please pass at least --pr-number")
        raise SystemExit(1)

    run.run_toolbox("jump_ci", "prepare_topsail", **prepare_topsail_args,)

    return None
