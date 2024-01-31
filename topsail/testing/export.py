import logging
logging.getLogger().setLevel(logging.INFO)
import os
import datetime
import json

from . import config, run, env

def export_artifacts(artifacts_dirname, test_step=None):
    if test_step and os.environ.get("PERFLAB_CI") == "true":
        logging.info("export_artifacts: in the PerfLab. Ignoring step export.")
        return

    if not config.ci_artifacts.get_config("export_artifacts.enabled"):
        logging.info("export_artifacts.enabled not set, nothing to do here.")
        return

    bucket = config.ci_artifacts.get_config("export_artifacts.bucket")
    path_prefix = config.ci_artifacts.get_config("export_artifacts.path_prefix")
    if not path_prefix:
        path_prefix = ""

    if os.environ.get("OPENSHIFT_CI") == "true":
        job_spec = json.loads(os.environ["JOB_SPEC"])
        pull_number = job_spec["refs"]["pulls"][0]["number"]
        github_org = job_spec["refs"]["org"]
        github_repo = job_spec["refs"]["repo"]
        job = job_spec["job"]
        build_id = job_spec["buildid"]

        run_id=f"prow/pull/{github_org}_{github_repo}/{pull_number}/{job}/{build_id}/artifacts"

    elif os.environ.get("PERFLAB_CI") == "true":
        logging.warning("No way to get the run identifiers from Jenkins in the PERFLAB_CI")
        run_id = f"middleware_jenkins/{int(datetime.datetime.now().timestamp())}"
    else:
        logging.error("CI engine not recognized, cannot build the run id ...")
        raise ValueError("CI engine not recognized, cannot build the run id ...")

    if test_step:
        run_id += f"/{test_step}"

    export_dest = f"s3://{bucket}/{path_prefix}/{run_id}"
    with open(env.ARTIFACT_DIR / "export_dest", "w") as f:
        print(export_dest, file=f)

    config.ci_artifacts.set_config("export_artifacts.dest", export_dest)

    aws_creds_filename = config.ci_artifacts.get_config("secrets.aws_credentials")
    run.run(f"AWS_SHARED_CREDENTIALS_FILE=\"$PSAP_ODS_SECRET_PATH/{aws_creds_filename}\" aws s3 cp --recursive \"{artifacts_dirname}\" \"{export_dest}\" &> {env.ARTIFACT_DIR / 'export_artifacts.log'}")
