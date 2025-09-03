import functools
import pathlib
import os, sys
import logging
import datetime
import yaml

from projects.core.library import env, config, run, export, common

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
CRC_MAC_AI_SECRET_PATH = pathlib.Path(os.environ.get("CRC_MAC_AI_SECRET_PATH", "/env/CRC_MAC_AI_SECRET_PATH/not_set"))


def apply_preset_from_kubeconfig():
    kubeconfig_file = os.environ.get("KUBECONFIG")
    if not kubeconfig_file:
        logging.info("No KUBECONFIG defined, no preset to apply")
        return

    try:
        with open(kubeconfig_file) as f:
            content = yaml.safe_load(f)
    except Exception as e:
        logging.error(f"Kubeconfig {kubeconfig_file} isn't a valid yaml file: {e}")
        return

    if not isinstance(content, dict):
        logging.info(f"Kubeconfig {kubeconfig_file} is empty or not a mapping; no preset to apply")
        return

    if content.get("clusters"):
        logging.info(f"Kubeconfig {kubeconfig_file} is a K8s kubeconfig.")

    if content.get("description"):
        logging.info(f"Kubeconfig description: {content['description']}")

    if "preset_name" in content:
        if not content['preset_name']:
            logging.info("Kubeconfig preset to apply: none")
        else:
            logging.info(f"Kubeconfig preset to apply: {content['preset_name']}")
            config.project.apply_preset(content['preset_name'])


initialized = False
def init(ignore_secret_path=False, apply_preset_from_pr_args=True):
    global initialized
    if initialized:
        logging.debug("Already initialized.")
        return
    initialized = True

    openshift_ci_update_artifact_dir()

    env.init()
    config.init(TESTING_THIS_DIR, apply_preset_from_pr_args)

    apply_preset_from_kubeconfig()

    if not ignore_secret_path:
        if not CRC_MAC_AI_SECRET_PATH.exists():
            raise RuntimeError(f"Path with the secrets (CRC_MAC_AI_SECRET_PATH={CRC_MAC_AI_SECRET_PATH}) does not exists.")

        run.run(f'sha256sum "$CRC_MAC_AI_SECRET_PATH"/* > "{env.ARTIFACT_DIR}/secrets.sha256sum"')


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


def openshift_ci_update_artifact_dir():
    if os.environ.get("OPENSHIFT_CI") != "true": return
    if os.environ.get("TOPSAIL_JUMP_CI_INSIDE_JUMP_HOST") != "true": return

    artifact_dir = os.environ["ARTIFACT_DIR"]
    if artifact_dir != "/logs/artifacts": return

    # in OpenShift CI, the test starts with ARTIFACT_DIR=/logs/artifacts
    # this ARTIFACT_DIR value cannot be used in the remote Mac (rootfs is readonly, so cannot cheat)
    #
    # below, we create a symlink from /tmp/topsail_$DATE to /logs/artifacts
    # and define ARTIFACT_DIR=/tmp/topsail_$DATE
    # so that the *jump-host* indirectly writes into /logs/artifacts
    # (that's where its artifacts will be collected from )
    # and the Mac writes into /tmp/topsail_$DATE
    # (where it's allowed to write)

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    new_artifact_dir = pathlib.Path("/tmp") / f"topsail_{ts}"

    logging.info(f"openshift_ci_update_artifact_dir: Creating a symlink {new_artifact_dir} --> {artifact_dir}")
    new_artifact_dir.symlink_to(artifact_dir)

    os.environ["ARTIFACT_DIR"] = str(new_artifact_dir)
