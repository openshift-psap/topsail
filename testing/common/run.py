import logging
logging.getLogger().setLevel(logging.INFO)

import subprocess

def run(command, capture_stdout=False, capture_stderr=False, check=True, protect_shell=True, cwd=None, stdin_file=None):
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
