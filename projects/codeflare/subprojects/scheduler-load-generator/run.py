import subprocess
import logging

def run(command, capture_stdout=False, capture_stderr=False, check=True, protect_shell=True, cwd=None, input=None):
    logging.info(f"run: {command}")
    args = {}

    args["cwd"] = cwd
    args["input"] = input.encode()
    if capture_stdout: args["stdout"] = subprocess.PIPE
    if capture_stderr: args["stderr"] = subprocess.PIPE
    if check: args["check"] = True

    if protect_shell:
        command = f"set -o errexit;set -o pipefail;set -o nounset;set -o errtrace;{command}"

    proc = subprocess.run(command, shell=True, **args)

    if capture_stdout: proc.stdout = proc.stdout.decode("utf8")
    if capture_stderr: proc.stderr = proc.stderr.decode("utf8")

    return proc

def run_in_background(command, input=None, verbose=True, capture_stdout=False):
    if verbose:
        logging.info(f"run in background: {command}")

    args = {}
    args["stdin"] = subprocess.PIPE
    if capture_stdout: args["stdout"] = subprocess.PIPE
    proc = subprocess.Popen(command, **args)
    proc.stdin.write(input.encode())
    proc.stdin.close()

    return proc
