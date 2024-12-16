from projects.core.library import env, config, run
from projects.jump_ci.testing import utils, tunnelling

@utils.entrypoint()
def lock_cluster():
    pass

@utils.entrypoint()
def unlock_cluster():
    pass

@utils.entrypoint()
def prepare():
    """
    Prepares the jump-host for running TOPSAIL commands.
    """

    tunnelling.prepare()

    run.run_toolbox("nfd", "has_labels")

    #
    # Clone the Git Repository
    #

    #
    # Build the image
    #

    #
    # Run the test
    #

    #
    # Download the artifacts
    #

    return None
