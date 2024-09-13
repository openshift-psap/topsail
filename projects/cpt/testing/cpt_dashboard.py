#!/usr/bin/env python

import sys, os
import pathlib
import subprocess
import logging
import datetime
import time
import functools

import yaml
import fire

from projects.core.library import env, config, run, configure_logging, prepare_user_pods
from projects.matrix_benchmarking.library import visualize

configure_logging()

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))

initialized = False
def init(ignore_secret_path=False, apply_preset_from_pr_args=True):
    global initialized
    if initialized:
        logging.debug("Already initialized.")
        return
    initialized = True

    env.init()
    config.init(TESTING_THIS_DIR)

    if apply_preset_from_pr_args:
        config.ci_artifacts.apply_preset_from_pr_args()

    if not ignore_secret_path:
        if not PSAP_ODS_SECRET_PATH.exists():
            raise RuntimeError(f"Path with the secrets (PSAP_ODS_SECRET_PATH={PSAP_ODS_SECRET_PATH}) does not exists.")

def entrypoint(ignore_secret_path=False, apply_preset_from_pr_args=True):
    def decorator(fct):
        @functools.wraps(fct)
        def wrapper(*args, **kwargs):
            init(ignore_secret_path, apply_preset_from_pr_args)
            fct(*args, **kwargs)

        return wrapper
    return decorator

# ---

@entrypoint()
def prepare_es():
    "Prepares the OpenSearch instance"
    secret_file = PSAP_ODS_SECRET_PATH / config.ci_artifacts.get_config("secrets.password_file")

    run.run_toolbox_from_config("cluster", "deploy_opensearch", extra=dict(secret_properties_file=str(secret_file)))


@entrypoint()
def prepare_cpt_backend():
    "Prepares the cluster for running the CPT Dashboard"

    run.run_toolbox_from_config("cluster", "build_push_image", prefix="dashboard", suffix="frontend", artifact_dir_suffix="_dashboard_frontend")
    run.run_toolbox_from_config("cluster", "build_push_image", prefix="dashboard", suffix="backend", artifact_dir_suffix="_dashboard_backend")


@entrypoint()
def deploy():
    "Deploys the CPT Dashboard"

    es_namespace = config.ci_artifacts.get_config("opensearch.namespace")
    es_instance = config.ci_artifacts.get_config("opensearch.name")
    secret_file = PSAP_ODS_SECRET_PATH / config.ci_artifacts.get_config("secrets.password_file")

    es_url = "https://" + run.run(f"oc get route/{es_instance} -n {es_namespace} -ojsonpath={{.spec.host}}", capture_stdout=True).stdout
    run.run_toolbox_from_config("cpt", "deploy_cpt_dashboard",
                                extra=dict(es_url=es_url, secret_properties_file=str(secret_file)))

# ---

@entrypoint()
def prepare_ci():
    "Prepares the CPT Dashboard"

    prepare_es()
    prepare_cpt_backend()


@entrypoint()
def test_ci():
    "Deploys the CPT Dashboard"

    deploy()


@entrypoint()
def cleanup_cluster_ci():
    if config.ci_artifacts.get_config("clusters.cleanup.opensearch"):
        es_namespace = config.ci_artifacts.get_config("opensearch.namespace")
        run.run(f"oc delete ns {es_namespace}")

    if config.ci_artifacts.get_config("clusters.cleanup.cpt.dashboard"):
        cpt_dashboard_namespace = config.ci_artifacts.get_config("cpt_dashboard.namespace")
        run.run(f"oc delete ns {cpt_dashboard_namespace}")

# ---

class Entrypoint:
    """
    Commands for launching the CI tests
    """

    def __init__(self):
        self.prepare_es = prepare_es
        self.prepare = prepare_cpt_backend
        self.deploy = deploy

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
