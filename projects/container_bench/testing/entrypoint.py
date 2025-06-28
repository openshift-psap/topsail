import functools
import pathlib
import os
import logging
import datetime

from projects.core.library import env, config, run
from constants import CONTAINER_BENCH_SECRET_PATH, TESTING_THIS_DIR

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

    if not ignore_secret_path:
        if not CONTAINER_BENCH_SECRET_PATH.exists():
            raise RuntimeError(
                f"Path with the secrets (CONTAINER_BENCH_SECRET_PATH={CONTAINER_BENCH_SECRET_PATH}) "
                "does not exists."
            )
        run.run(f'sha256sum "$CONTAINER_BENCH_SECRET_PATH"/* > "{env.ARTIFACT_DIR}/secrets.sha256sum"')


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
    if os.environ.get("OPENSHIFT_CI") != "true":
        return
    if os.environ.get("TOPSAIL_JUMP_CI_INSIDE_JUMP_HOST") != "true":
        return

    artifact_dir = os.environ["ARTIFACT_DIR"]
    if artifact_dir != "/logs/artifacts":
        return

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

    logging.info(
        f"openshift_ci_update_artifact_dir: Creating a symlink {new_artifact_dir} --> {artifact_dir}"
    )
    new_artifact_dir.symlink_to(artifact_dir)

    os.environ["ARTIFACT_DIR"] = str(new_artifact_dir)
