#! /usr/bin/env python

import logging
logging.getLogger().setLevel(logging.INFO)
import os, sys
import json
import subprocess
import functools
import pathlib

import fire

from projects.core.library import config, run, env


def init():
    env.init()
    config_file = os.environ.get("TOPSAIL_FROM_CONFIG_FILE")
    if not config_file:
        raise RuntimeError("TOPSAIL_FROM_CONFIG_FILE must be set. Please source your `configure.sh` before running this file.")

    config.init(pathlib.Path(config_file).parent)


def entrypoint():
    def decorator(fct):
        @functools.wraps(fct)
        def wrapper(*args, **kwargs):
            init()
            fct(*args, **kwargs)

        return wrapper
    return decorator


@entrypoint()
def export_artifacts(artifacts_dirname, test_step=None):
    if test_step and os.environ.get("PERFLAB_CI") == "true":
        logging.info("export_artifacts: in the PerfLab. Ignoring step export.")
        return

    if not config.project.get_config("export_artifacts.enabled"):
        logging.info("export_artifacts.enabled not set, nothing to do here.")
        return

    bucket = config.project.get_config("export_artifacts.bucket")
    path_prefix = config.project.get_config("export_artifacts.path_prefix")
    if not path_prefix:
        path_prefix = ""

    if os.environ.get("OPENSHIFT_CI") == "true":
        job_spec = json.loads(os.environ["JOB_SPEC"])
        pull_number = job_spec["refs"]["pulls"][0]["number"]
        job = job_spec["job"]
        build_id = job_spec["buildid"]

        run_id=f"prow/{pull_number}/{build_id}"

    elif os.environ.get("PERFLAB_CI") == "true":
        logging.warning("No way to get the run identifiers from Jenkins in the PERFLAB_CI")


        build_number = os.environ["JENKINS_BUILD_NUMBER"]
        job = os.environ["JENKINS_JOB"] # "job/ExternalTeams/job/RHODS/job/topsail"
        job_id = job[4:].replace("/job/", "_")

        run_id = f"middleware_jenkins/{job_id}/{build_number}"
    else:
        logging.error("CI engine not recognized, cannot build the run id ...")
        raise ValueError("CI engine not recognized, cannot build the run id ...")

    if test_step:
        run_id += f"/{test_step}"

    export_dest = f"s3://{bucket}/{path_prefix}/{run_id}"
    export_url = f"https://{bucket}.s3.amazonaws.com/index.html#{path_prefix}/{run_id}/"
    with open(env.ARTIFACT_DIR / "export.url", "w") as f:
        print(export_url, file=f)

    config.project.set_config("export_artifacts.dest", export_url)

    logging.info(f"Exporting to {export_dest} ({export_url})")
    aws_creds_filename = config.project.get_config("secrets.aws_credentials")
    run.run(f"AWS_SHARED_CREDENTIALS_FILE=\"$PSAP_ODS_SECRET_PATH/{aws_creds_filename}\" aws s3 cp --recursive \"{artifacts_dirname}\" \"{export_dest}\" --acl public-read &> {env.ARTIFACT_DIR / 'aws_s3_cp.log'}")



class Export:
    """
    Commands for launching the artifacts export
    """

    def __init__(self):
        self.export_artifacts = export_artifacts


def main():
    # Print help rather than opening a pager
    fire.core.Display = lambda lines, out: print(*lines, file=out)

    fire.Fire(Export())


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{e.cmd}' failed --> {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print() # empty line after ^C
        logging.error(f"Interrupted.")
        sys.exit(1)
