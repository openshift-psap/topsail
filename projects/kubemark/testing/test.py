import yaml
import fire

from projects.core.library import env, config, run, visualize, configure_logging, prepare_user_pods
configure_logging()


TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent


initialized = False
def init(ignore_secret_path=False, apply_preset_from_pr_args=True):
    global initialized
    if initialized:
        logging.debug("Already initialized.")
        return
    initialized = True

    env.init()
    #config.init(TESTING_THIS_DIR)

    #if apply_preset_from_pr_args:
    #    config.ci_artifacts.apply_preset_from_pr_args()


def entrypoint(ignore_secret_path=False, apply_preset_from_pr_args=True):
    def decorator(fct):
        @functools.wraps(fct)
        def wrapper(*args, **kwargs):
            init(ignore_secret_path, apply_preset_from_pr_args)
            fct(*args, **kwargs)

        return wrapper
    return decorator


@entrypoint()
def test_ci():
    """
    Runs the test from the CI
    """

    run.run("echo hello world")


@entrypoint()
def prepare_ci():
    """
    Prepares the cluster and the namespace for running the tests
    """

    run.run_toolbox("cluster deploy_kubemark_capi_provider")
    run.run_toolbox("cluster deploy_kubemark_nodes")


@entrypoint()
def cleanup_cluster():
    """
    Restores the cluster to its original state
    """
    # _Not_ executed in OpenShift CI cluster (running on AWS). Only required for running in bare-metal environments.

    pass

# ---

class Entrypoint:
    """
    Commands for launching the CI tests
    """

    def __init__(self):
        self.cleanup_cluster_ci = cleanup_cluster

        self.prepare_ci = prepare_ci

        self.test_ci = test_ci


def main():
    # Print help rather than opening a pager
    fire.core.Display = lambda lines, out: print(*lines, file=out)

    fire.Fire(Entrypoint())


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{e.cmd}' failed --> {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print() # empty line after ^C
        logging.error(f"Interrupted.")
        sys.exit(1)
