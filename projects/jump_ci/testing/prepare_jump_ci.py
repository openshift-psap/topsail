import os
import logging

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

        override_cluster = config.project.get_config("overrides.PR_POSITIONAL_ARG_1")
        config.project.set_config("cluster.name", override_cluster)

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
        prepare_topsail_args |= dict(
            repo_owner=os.environ["REPO_OWNER"],
            repo_name=os.environ["REPO_NAME"],
            pr_number=os.environ["PULL_NUMBER"],
            git_ref=os.environ["PULL_PULL_SHA"]
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
