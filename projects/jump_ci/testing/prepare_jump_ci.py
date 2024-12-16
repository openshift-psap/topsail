import os

from projects.core.library import env, config, run
from projects.jump_ci.testing import utils, tunnelling

CLUSTER_LOCK = "icelake"

@utils.entrypoint()
def lock_cluster(cluster_lock=CLUSTER_LOCK,):
    """
    Take the lock on a given cluster

    Args:
      cluster_lock: Name of the cluster lock to use
    """
    # Open the tunnel
    tunnelling.prepare()

    run.run_toolbox("jump_ci", "take_lock", cluster=CLUSTER_LOCK)

    prepare()


@utils.entrypoint()
def unlock_cluster(cluster_lock=CLUSTER_LOCK,):
    """
    Release the lock on a given cluster

    Args:
      cluster_lock: Name of the cluster lock to use
    """
    # Open the tunnel
    tunnelling.prepare()

    run.run_toolbox("jump_ci", "release_lock", cluster=CLUSTER_LOCK)


@utils.entrypoint()
def prepare(
        cluster_lock=CLUSTER_LOCK,
        repo_owner=None,
        repo_name=None,
        pr_number=None,
):
    """
    Prepares the jump-host for running TOPSAIL commands.
    Args:
      cluster_lock: Name of the cluster lock to use
      owner: Name of the Github repo owner
      repo: Name of the TOPSAIL github repo
      pr_number: PR number to use for the test. If none, use the main branch.
    """

    # Open the tunnel
    tunnelling.prepare()

    # Lock the cluster
    run.run_toolbox("jump_ci", "ensure_lock", cluster=cluster_lock)

    # Clone the Git Repository
    # Build the image
    prepare_topsail_args = dict(cluster_lock=cluster_lock)
    if any([repo_owner, repo_name, pr_number]):
        if not all([repo_owner, repo_name, pr_number]):
            raise RuntimeError("Missing parameters in the CLI arguments ...")
        prepare_topsail_args |= dict(
            repo_owner=repo_owner,
            repo_name=repo_name,
            pr_number=pr_number,
        )

    elif os.environ.get("OPENSHIFT_CI") == "true":
        prepare_topsail_args |= dict(
            repo_owner=os.environ["REPO_OWNER"],
            repo_name=os.environ["REPO_NAME"],
            pr_number=os.environ["PULL_NUMBER"]
        )

    else:
        raise RuntimeError("Couldn't determine the CI environment ...")

    run.run_toolbox("jump_ci", "prepare_topsail", **prepare_topsail_args,)

    return None
