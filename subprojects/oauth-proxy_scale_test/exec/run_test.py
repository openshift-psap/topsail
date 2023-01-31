#! /usr/bin/python -u

import types
import datetime
import subprocess
import os, sys
import pathlib
import time
import psutil
import logging
logging.getLogger().setLevel(logging.INFO)

BENCHMARK_NAME = "oauth-proxy_scale_test"
ARTIFACT_DIR = None

CI_ARTIFACTS_DIR = pathlib.Path(__file__).parent.parent.parent.parent

def prepare_settings():

    settings = types.SimpleNamespace()
    for arg in sys.argv[1:]:
        k, _, v = arg.partition("=")
        settings.__dict__[k] = v

    return settings

def set_artifacts_dir():
    global ARTIFACT_DIR

    if sys.stdout.isatty():
        base_dir = pathlib.Path("/tmp") / ("ci-artifacts_" + datetime.datetime.today().strftime("%Y%m%d"))
        base_dir.mkdir(exist_ok=True)
        current_length = len(list(base_dir.glob("*__*")))
        ARTIFACT_DIR = base_dir / f"{current_length:03d}__{BENCHMARK_NAME}"
        ARTIFACT_DIR.mkdir(exist_ok=True)
    else:
        ARTIFACT_DIR = pathlib.Path(os.getcwd())

    logging.info(f"Saving artifacts files into {ARTIFACT_DIR}")

    os.environ["ARTIFACT_DIR"] = str(ARTIFACT_DIR)


def run(command):
    return subprocess.run(command, check=True, shell=True)

def run_toolbox(command):
    return subprocess.run(f"cd {CI_ARTIFACTS_DIR} && "+command, check=True, shell=True)

def kill(subprocess):
    process = psutil.Process(subprocess.pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()

def main():
    logging.info(f"{datetime.datetime.now()} | Running with:")
    for kv in sys.argv[1:]:
        logging.info(f" - {kv}")

    settings = prepare_settings()
    set_artifacts_dir()

    logging.info("Reset Prometheus metrics ...")
    run_toolbox("./run_toolbox.py cluster reset_prometheus_db > /dev/null")

    target = f"{settings.protocol}://{settings.host}.{settings.server}{settings.path}"
    logging.info(f"Running the test against {target} with {settings.number_of_cores} cores for {settings.duration}s")

    processes = []
    try:
        for core in range(int(settings.number_of_cores)):
            curl_command = f"while true; do curl -Ssf -k {target} > /dev/null; done"
            processes.append(subprocess.Popen(curl_command, shell=True, stdout=subprocess.PIPE))

        logging.info(f"{datetime.datetime.now()} | Sleeping for {settings.duration} seconds ...")
        time.sleep(int(settings.duration))
        logging.info(f"{datetime.datetime.now()} | Sleeping for {settings.duration} seconds ... done.")

    except KeyboardInterrupt:
        for proc in processes:
            kill(proc)

        raise

    for proc in processes:
        kill(proc)

    logging.info("Collecting Prometheus metrics ...")
    run_toolbox("./run_toolbox.py cluster dump_prometheus_db  > /dev/null")
    logging.info("All done.")

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logging.error("\nInterrupted ...")
        sys.exit(1)
