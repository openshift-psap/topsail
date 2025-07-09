import pathlib
import logging
import functools
import tempfile
import os

from projects.core.library import env, config

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent

def apply_preset_by_jobname():
    if os.environ.get("OPENSHIFT_CI") != "true":
        logging.info("apply_preset_by_jobname: not running in Openshift CI, skipping")
        return

    job_name = os.environ["JOB_NAME"]

    presets = config.project.get_config("prepare.job_name_to_preset")
    preset_name = presets.get(job_name)
    if not preset_name:
        logging.info(f"apply_preset_by_jobname: no preset to apply to apply for '{job_name}'")
        return

    logging.info(f"apply_preset_by_jobname: applying the '{preset_name}' preset for job name '{job_name}' ...")
    config.project.apply_preset(preset_name)


initialized = False
def init(ignore_secret_path=False, apply_preset_from_pr_args=True):
    global initialized
    if initialized:
        logging.debug("Already initialized.")
        return
    initialized = True

    env.init()
    config.init(TESTING_THIS_DIR, apply_config_overrides=False)
    config.project.apply_config_overrides(ignore_not_found=True)
    apply_preset_by_jobname()
    config.test_skip_list()


def entrypoint(ignore_secret_path=False):
    apply_preset_from_pr_args=False
    def decorator(fct):
        @functools.wraps(fct)
        def wrapper(*args, **kwargs):
            init(ignore_secret_path, apply_preset_from_pr_args)
            fct(*args, **kwargs)

        return wrapper
    return decorator


__keep_open = []
def get_tmp_fd():
    # generate a fd-only temporary file
    fd, file_path = tempfile.mkstemp()

    # using only the FD. Ensures that the file disappears when this
    # process terminates
    os.remove(file_path)

    py_file = os.fdopen(fd, 'w')
    # this makes sure the FD isn't closed when the var goes out of
    # scope
    __keep_open.append(py_file)

    return f"/proc/{os.getpid()}/fd/{fd}", py_file


def get_lock_owner():
    if os.environ.get("OPENSHIFT_CI") == "true":
        build_id = os.environ["BUILD_ID"]
        if "PULL_NUMBER" in os.environ:
            pr = os.environ["PULL_NUMBER"]
            return f"openshift_ci__pr{pr}__build{build_id}"
        else:

            return f"openshift_ci__periodic__build{build_id}"
    else:
        logging.warning("Not running in a known CI. Using the username as lock owner.")
        return os.environ["USER"]
