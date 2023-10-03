import sys, os, signal
import traceback
import logging
logging.getLogger().setLevel(logging.INFO)

import subprocess

import joblib

from . import env

# create new process group, become its leader
os.setpgrp()

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
