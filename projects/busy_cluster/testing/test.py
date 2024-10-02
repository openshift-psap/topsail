#!/usr/bin/env python

import sys, os
import pathlib
import subprocess
import logging
logging.getLogger().setLevel(logging.INFO)
import datetime
import time
import functools
import uuid

import yaml
import fire

from projects.core.library import env, config, run, export, common
from projects.matrix_benchmarking.library import visualize

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))
LIGHT_PROFILE = "light"
METAL_PROFILE = "metal"

initialized = False
def init(ignore_secret_path=False, apply_preset_from_pr_args=True):
    global initialized
    if initialized:
        logging.debug("Already initialized.")
        return
    initialized = True

    env.init()
    config.init(TESTING_THIS_DIR, apply_preset_from_pr_args)

    if not ignore_secret_path:
        if not PSAP_ODS_SECRET_PATH.exists():
            raise RuntimeError(f"Path with the secrets (PSAP_ODS_SECRET_PATH={PSAP_ODS_SECRET_PATH}) does not exists.")

        run.run(f'sha256sum "$PSAP_ODS_SECRET_PATH"/* > "{env.ARTIFACT_DIR}/secrets.sha256sum"', check=False)

    config.project.detect_apply_light_profile(LIGHT_PROFILE)
    is_metal = config.project.detect_apply_metal_profile(METAL_PROFILE)

    if is_metal:
        metal_profiles = config.project.get_config("clusters.metal_profiles")
        profile_applied = config.project.detect_apply_cluster_profile(metal_profiles)

        if not profile_applied:
            raise ValueError("Bare-metal cluster not recognized :/ ")


def entrypoint(ignore_secret_path=False, apply_preset_from_pr_args=True):
    def decorator(fct):
        @functools.wraps(fct)
        def wrapper(*args, **kwargs):
            init(ignore_secret_path, apply_preset_from_pr_args)
            exit_code = fct(*args, **kwargs)
            logging.info(f"exit code of {fct.__qualname__}: {exit_code}")
            if exit_code is None:
                exit_code = 0
            raise SystemExit(exit_code)

        return wrapper
    return decorator


@entrypoint()
def prepare_ci():
    """
    Prepares the cluster and the namespace for running the tests
    """

    run.run_toolbox("busy_cluster", "create_namespaces")
    run.run_toolbox("busy_cluster", "create_configmaps")
    run.run_toolbox("busy_cluster", "create_configmaps", as_secrets=True)
    run.run_toolbox("busy_cluster", "create_deployments")
    run.run_toolbox("busy_cluster", "create_jobs")


@entrypoint()
def test_ci():
    """
    Runs the test from the CI
    """

    run.run_toolbox("busy_cluster", "status")

    if config.project.get_config("clusters.cleanup_on_exit"):
        cleanup_cluster_ci()


@entrypoint()
def cleanup_cluster_ci():
    """
    Runs the cluster cleanup
    """

    run.run_toolbox("busy_cluster", "cleanup")


class Entrypoint:
    """
    Commands for launching the CI tests
    """

    def __init__(self):
        self.prepare_ci = prepare_ci
        self.test_ci = test_ci
        self.cleanup_cluster_ci = cleanup_cluster_ci


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
