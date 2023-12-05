#! /usr/bin/env python

import sys, os
import pathlib
import subprocess
import logging
import yaml

import fire

import test
import test_e2e
import test_scale

PSAP_ODS_SECRET_PATH = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH", "/env/PSAP_ODS_SECRET_PATH/not_set"))

from topsail.testing import env, config, run, configure_logging
configure_logging()

def deploy(
        model_name,
        min_replicas=1,
        namespace=None,
        include_secret_key=False,
        index=None,
        show=False,
        mute_serving_logs=False,
        delete_other_models=False,
        limits_equals_requests=False,
        ):
    """
    Deploys a preconfigured model

    Args:
      namespace: the namespace where the model should be deployed. If omitted, deploys in the current namespace.
      model_name: the name of the model to deploy.
      min_replicas: the minimum number of replicas to request.
      include_secret_key: if True, deploy the secret parameters from the secret file.
      index: if set, picks up the model definition in the config file (key: tests.e2e.models[index])
      show: if True, only show the model configuration, do not deploy it.
      mute_serving_logs: if True, mutes the stdout logs of the KServe container (to avoid leaking secrets)
      delete_other_models: if True, deletes the other models already deployed in the namespace
      limits_equals_requests: if True, sets the CPU and memory limits to their request value. If False, do not set them.
    """

    model_config = test_e2e.consolidate_model(index, name=(model_name if index is None else None), show=False)

    if namespace is None:
        namespace = run.run("oc config view --minify -ojsonpath='{..namespace}'", capture_stdout=True).stdout
        logging.info(f"Using namespace '{namespace}'.")

    model_config["inference_service"]["min_replicas"] = min_replicas

    if not include_secret_key and "secret_key" in model_config:
        logging.info(f"Removing the secret key parameter: {model_config['secret_key']}")
        del model_config["secret_key"]

    # ---

    dump = yaml.dump(model_config,  default_flow_style=False, sort_keys=False).strip()
    logging.info(f"Configuration for model '{model_name}':\n{dump}")

    if show: return

    # ---

    test_e2e.deploy_consolidated_model(model_config, namespace, mute_serving_logs, delete_other_models, limits_equals_requests)


class Entrypoint:
    """
    Commands for deploying WatsonX models
    """

    def __init__(self):
        self.deploy = deploy


def main():
    # Print help rather than opening a pager
    fire.core.Display = lambda lines, out: print(*lines, file=out)

    fire.Fire(Entrypoint())


if __name__ == "__main__":
    try:
        from test import init
        init(ignore_secret_path=False, apply_preset_from_pr_args=True)

        sys.exit(main())
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{e.cmd}' failed --> {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print() # empty line after ^C
        logging.error(f"Interrupted.")
        sys.exit(1)
