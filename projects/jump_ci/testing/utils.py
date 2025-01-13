import pathlib
import logging
import functools
import tempfile
import os

from projects.core.library import env, config

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent

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
        pr = os.environ["PULL_NUMBER"]
        build_id = os.environ["BUILD_ID"]
        return f"pr{pr}__{build_id}"
    else:
        logging.warning("Not running in a known CI. Using the username as lock owner.")
        return os.environ["USER"]
