import sys, os, signal
import traceback
import logging
logging.getLogger().setLevel(logging.INFO)
import json
import signal

import subprocess

import joblib

from . import env

# create new process group, become its leader, except if we're already pid 1 (defacto group leader, setpgrp gets permission denied error)
try:
    if os.getpid() != 1:
        os.setpgrp()
except Exception as e:
    logging.warning(f"Cannot call os.setpgrp: {e}")


class SignalError(SystemExit):
    def __init__(self, sig, frame):
        self.sig = sig
        self.frame = frame

    def __str__(self):
        return f"SignalError(sig={self.sig})"

def raise_signal(sig, frame):
    raise SignalError(sig, frame)
signal.signal(signal.SIGINT, raise_signal)
signal.signal(signal.SIGTERM, raise_signal)


def run_toolbox_from_config(group, command, prefix=None, suffix=None, show_args=None, extra=None, artifact_dir_suffix=None, mute_stdout=False, check=True, run_kwargs=None):
    if extra is None:
        extra = {}

    if run_kwargs is None:
        run_kwargs = {}

    kwargs = dict()
    if prefix is not None:
        kwargs["prefix"] = prefix
    if suffix is not None:
        kwargs["suffix"] = suffix
    if extra is not None:
        kwargs["extra"] = extra
    if show_args:
        kwargs["show_args"] = show_args

    if mute_stdout:
        run_kwargs["capture_stdout"] = True

    if check is not None:
        run_kwargs["check"] = check

    env_vals = [f'ARTIFACT_DIR="{env.ARTIFACT_DIR}"']
    if artifact_dir_suffix is not None:
        env_vals.append(f'ARTIFACT_TOOLBOX_NAME_SUFFIX="{artifact_dir_suffix}"')

    cmd_env = " ".join(env_vals)

    return run(f'{cmd_env} ./run_toolbox.py from_config {group} {command} {_dict_to_run_toolbox_args(kwargs)}', **run_kwargs)


def _dict_to_run_toolbox_args(args_dict):
    args = []
    for k, v in args_dict.items():
        if isinstance(v, dict) or isinstance(v, list):
            val = json.dumps(v)
            arg = f"--{k}=\"{v}\""
        else:
            val = str(v).replace("'", "\'")
            arg = f"--{k}='{v}'"
        args.append(arg)

    return " ".join(args)


def run_toolbox(group, command, artifact_dir_suffix=None, run_kwargs=None, mute_stdout=None, check=None, **kwargs):
    if run_kwargs is None:
        run_kwargs = {}

    if mute_stdout:
        run_kwargs["capture_stdout"] = True

    if check is not None:
        run_kwargs["check"] = check

    env_vals = [f'ARTIFACT_DIR="{env.ARTIFACT_DIR}"']
    if artifact_dir_suffix is not None:
        env_vals.append(f'ARTIFACT_TOOLBOX_NAME_SUFFIX="{artifact_dir_suffix}"')

    cmd_env = " ".join(env_vals)

    return run(f'{cmd_env} ./run_toolbox.py {group} {command} {_dict_to_run_toolbox_args(kwargs)}', **run_kwargs)


def run(command, capture_stdout=False, capture_stderr=False, check=True, protect_shell=True, cwd=None, stdin_file=None, log_command=True):
    if log_command:
        logging.info(f"run: {command}")

    args = {}

    args["cwd"] = cwd
    args["shell"] = True

    if capture_stdout: args["stdout"] = subprocess.PIPE
    if capture_stderr: args["stderr"] = subprocess.PIPE
    if check: args["check"] = True
    if stdin_file:
        if not hasattr(stdin_file, "fileno"):
            raise ValueError("Argument 'stdin_file' must be an open file (with a file descriptor)")
        args["stdin"] = stdin_file

    if protect_shell:
        command = f"set -o errexit;set -o pipefail;set -o nounset;set -o errtrace;{command}"

    proc = subprocess.run(command, **args)

    if capture_stdout: proc.stdout = proc.stdout.decode("utf8")
    if capture_stderr: proc.stderr = proc.stderr.decode("utf8")

    return proc

class Parallel(object):
    def __init__(self, name, exit_on_exception=True, dedicated_dir=True):
        self.name = name
        self.parallel_tasks = None
        self.exit_on_exception = exit_on_exception
        self.dedicated_dir = dedicated_dir

    def __enter__(self):
        self.parallel_tasks = []

        return self

    def delayed(self, function, *args, **kwargs):
        self.parallel_tasks += [joblib.delayed(function)(*args, **kwargs)]

    def __exit__(self, ex_type, ex_value, exc_traceback):

        if ex_value:
            logging.warning(f"An exception occured while preparing the '{self.name}' Parallel execution ...")
            return False

        if self.dedicated_dir:
            context = env.NextArtifactDir(self.name)
        else:
            context = open("/dev/null") # dummy context

        with context:
            try:
                joblib.Parallel(n_jobs=-1, backend="threading")(self.parallel_tasks)
            except Exception as e:
                if not self.exit_on_exception:
                    raise e

                traceback.print_exc()

                logging.error(f"Exception caught during the '{self.name}' Parallel execution. Exiting.")
                # kill all processes in my group
                # (the group was started with the os.setpgrp() above)
                os.killpg(0, signal.SIGKILL)
                sys.exit(1)

        return False # If we returned True here, any exception would be suppressed!


def run_and_catch(exc, fct, *args, **kwargs):
    """
    Helper function for chaining multiple functions without swallowing exceptions
    Example:

    exc = None
    exc = run.run_and_catch(
      exc,
      run.run_toolbox, "kserve", "capture_operators_state", run_kwargs=dict(capture_stdout=True),
    )

    exc = run.run_and_catch(
      exc,
      run.run_toolbox, "cluster", "capture_environment", run_kwargs=dict(capture_stdout=True),
    )

    if exc: raise exc
    """
    if not (exc is None or isinstance(exc, Exception)):
        raise ValueException(f"exc={exc} should be None or an Exception")

    try:
        fct(*args, **kwargs)
    except Exception as e:
        logging.error(f"{e.__class__.__name__}: {e}")
        exc = exc or e
    return exc
