#! /usr/bin/env python3

import fire
import sys, os
import yaml
import pathlib
import jsonpath_ng
import copy
from collections import defaultdict

import logging
logging.getLogger().setLevel(logging.INFO)

import subprocess

import k8s_quantity

ARTIFACT_DIR = pathlib.Path(os.environ.get("ARTIFACT_EXTRA_LOGS_DIR", os.environ.get("ARTIFACT_DIR", ".")))

def run(command, capture_stdout=False, capture_stderr=False, check=True, protect_shell=True, cwd=None):
    logging.info(f"run: {command}")
    args = {}

    args["cwd"] = cwd
    if capture_stdout: args["stdout"] = subprocess.PIPE
    if capture_stderr: args["stderr"] = subprocess.PIPE
    if check: args["check"] = True

    if protect_shell:
        command = f"set -o errexit;set -o pipefail;set -o nounset;set -o errtrace;{command}"

    proc = subprocess.run(command, shell=True, **args)

    if capture_stdout: proc.stdout = proc.stdout.decode("utf8")
    if capture_stderr: proc.stderr = proc.stderr.decode("utf8")

    return proc


with open(pathlib.Path(__file__).parent / "base_appwrapper.yaml") as f:
    base_appwrapper = yaml.safe_load(f)

with open(pathlib.Path(__file__).parent / "config.yaml") as f:
    main_config = yaml.safe_load(f)

def get_config(jsonpath, config=main_config):
    return jsonpath_ng.parse(jsonpath).find(config)[0].value

def set_config(config, jsonpath, value):
    get_config(jsonpath, config=config) # will raise an exception if the jsonpath does not exist
    jsonpath_ng.parse(jsonpath).update(config, value)

# https://stackoverflow.com/questions/1094841/get-human-readable-version-of-file-size
def sizeof_fmt(num, suffix=""):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"

def main(dry_run=True,
         namespace=None,
         job_template_name="sleeper",
         job_mode=False,
         pod_count=1,
         pod_runtime=30,
         pod_requests={"cpu": "1"},
         aw_base_name="appwrapper",
         aw_priority=10,
         aw_count=3,
         timespan=0,
         ):
    """
    Generates workload for the MCAD load test

    Args:
      dry_run: if True (default), only prepares the resources. If False, instanciate them in the cluster
      namespace: namespace in which the workload should be instanciated
      job_template_name: name of the job template to use inside the AppWrapper
      job_mode: if true, create Jobs instead of AppWrappers
      pod_count: number of Pods to create in each of the AppWrappers
      pod_runtime: run time parameter to pass to the Pod
      pod_requests: requests to pass to the Pod definition
      aw_base_name: name prefix for the AppWrapper resources
      aw_priority: priority to set in the AppWrapper
      aw_count: number of AppWrapper replicas to create
      timespan: number of minutes over which the AppWrappers should be created
    """

    if namespace is None:
        logging.info("Getting the current project name ...")

        namespace = run("oc project --short", capture_stdout=True).stdout.strip() \
            if not dry_run else "<DRY RUN>"

    logging.info(f"Using namespace '{namespace}' to deploy the workload.")

    if job_mode:
        logging.info("Running in Job mode")

    logging.info(f"Running with a timespan of {timespan} minutes.")

    set_config(base_appwrapper, "metadata.name", aw_base_name)
    set_config(base_appwrapper, "metadata.namespace", namespace)
    set_config(base_appwrapper, "spec.priority", aw_priority)

    job_templates = get_config("job_templates")

    job_template = job_templates.get(job_template_name)
    if not job_template:
        logging.error(f"Could not find the requested job template '{job_template_name}'. Available names: {','.join(job_templates.keys())}")
        sys.exit(1)

    for aw_index in range(aw_count):
        appwrapper = copy.deepcopy(base_appwrapper)
        appwrapper_name = f"aw{aw_index:03d}-{pod_runtime}s"

        set_config(appwrapper, "metadata.name", appwrapper_name)

        job = copy.deepcopy(job_template)
        job_name = f"{appwrapper_name}-job"
        set_config(job, "metadata.name", job_name)
        set_config(job, "metadata.namespace", namespace)
        set_config(job, "spec.template.spec.containers[0].env[0].value", str(pod_runtime))
        set_config(job, "spec.template.spec.containers[0].resources.limits", copy.deepcopy(pod_requests))
        set_config(job, "spec.template.spec.containers[0].resources.requests", copy.deepcopy(pod_requests))

        aw_genericitems = [dict(
            replicas = pod_count,
            completionstatus = "Complete",
            custompodresources=[dict(
                replicas=1,
                requests=copy.deepcopy(pod_requests),
                limits=copy.deepcopy(pod_requests),
            )],
            generictemplate = job,
        )]
        set_config(appwrapper, "spec.resources.GenericItems", aw_genericitems)

        if job_mode:
            src_file = ARTIFACT_DIR / f"job_{appwrapper_name}.yaml"
            with open(src_file, "w") as f:
                for item in appwrapper["spec"]["resources"]["GenericItems"]:
                    replica = item["replicas"] # currently ignored
                    job = item["generictemplate"]

                    yaml.dump(job, f)
                    print("---", file=f)
        else:
            src_file = ARTIFACT_DIR / f"{appwrapper_name}.yaml"
            with open(src_file, "w") as f:
                yaml.dump(appwrapper, f)

        command = f"oc apply -f {src_file}"
        if dry_run:
            logging.info(f"DRY_RUN: {command}")
        else:
            run(command)

    print(f"""---\n# Summary: {aw_count} AppWrappers, with each:
#  - {pod_count} Pods with {pod_requests}
#  - running for {pod_runtime} seconds
---
""")


if __name__ == "__main__":
    try:
        # Print help rather than opening a pager
        fire.core.Display = lambda lines, out: print(*lines, file=out)

        fire.Fire(main)
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{e.cmd}' failed --> {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print() # empty line after ^C
        logging.error(f"Interrupted.")
        sys.exit(1)
