import time
import datetime
import os, sys
import pathlib
import tarfile
import logging
import time

import get_leader

logging.getLogger().setLevel(logging.INFO)

LOCUST_FILE_PREFIX="locust_scale_test"

LOCUST_COORDINATOR_CMD = f"cd $LOCUST_DIR; PYTHONUNBUFFERED=1 locust --headless \
    --csv $ARTIFACT_DIR/{ LOCUST_FILE_PREFIX } \
    --csv-full-history \
    --html $ARTIFACT_DIR/{ LOCUST_FILE_PREFIX }.html \
    --only-summary \
     > $ARTIFACT_DIR/{ LOCUST_FILE_PREFIX }.stdout \
    2> $ARTIFACT_DIR/{ LOCUST_FILE_PREFIX }.stderr \
"
LOCUST_WORKER_CMD = f"cd $LOCUST_DIR; PYTHONUNBUFFERED=1 locust"

LOCUST_REPORTER_CMD = f"locust-reporter \
    -prefix $ARTIFACT_DIR/{ LOCUST_FILE_PREFIX } \
    -failures=true \
    -outfile $ARTIFACT_DIR/{LOCUST_FILE_PREFIX}_report.html \
"

REMOVE_NA_CMD = "sed -i '/N\/A/d' {file}"

artifacts_directory = pathlib.Path(os.getenv("ARTIFACT_DIR"))

def main():
    locust_scale_test_name = os.getenv("LOCUST_SCALE_TEST_NAME")

    rhods_dashboard = os.getenv("ODH_DASHBOARD_URL")
    rhods_version = os.getenv("RHODS_VERSION")

    username_prefix = os.getenv("TEST_USERS_USERNAME_PREFIX")
    job_completion_index = os.getenv("JOB_COMPLETION_INDEX", 0)
    idp_name = os.getenv("TEST_USERS_IDP_NAME")
    creds_file = os.getenv("CREDS_FILE")
    rank = int(os.getenv("JOB_COMPLETION_INDEX", -1))

    result_dest = pathlib.Path(os.getenv("ARTIFACT_DIR")) / LOCUST_FILE_PREFIX
    os.environ["RESULTS_DEST"] = str(result_dest)

    logging.info(f"Running locust test: {locust_scale_test_name}")
    logging.info(f"Against RHODS {rhods_dashboard} version {rhods_version}")
    logging.info(f"With Identity provider {idp_name}")

    logging.info(f"Storing artifacts in {artifacts_directory}")
    artifacts_directory.mkdir(parents=True, exist_ok=True)

    locust_test_cmd = LOCUST_COORDINATOR_CMD
    if rank == -1:
        logging.info("Running Locust standalone")
        pass # do not setup master/worker flags
    elif rank == 0:
        logging.info("Running Locust in leader mode")
        locust_test_cmd += " --master"
    else:
        logging.info("Running Locust in worker mode")
        retries = 5
        time.sleep(5)
        while True:
            leader_ip = get_leader.get_leader_ip()
            if leader_ip:
                logging.info(f"Found the Locust leader Pod IP address: {leader_ip} ... ")
                break
            elif leader_ip is None:
                logging.warning("Failed to find the Locust leader Pod ... ")
            else:
                logging.warning("Failed to find the Locust leader Pod IP address ... ")

            retries -= 1
            if retries == 0:

                return 255
            time.sleep(5)

        del os.environ["LOCUST_RUN_TIME"] # locust workers don't like it ...
        del os.environ["LOCUST_ITERATIONS"] # locust workers don't like it ...
        locust_test_cmd = f"{LOCUST_WORKER_CMD} --worker --master-host {leader_ip}"

    test_retcode = os.system(locust_test_cmd)

    if rank < 1:
        # Prevent this error of Locust-reporter:
        # `Stats CSV marshalling error record on line 0; parse error on line 6, column 12: strconv.ParseFloat: parsing "N/A": invalid syntax`
        # which happens when an exception is raised and gives lines like this:
        # `POST,/api/k8s/apis/project.openshift.io/v1/projectrequests/{project_name},0,0,0,0,0,0,0,0.0,0.0,N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A`

        os.system(REMOVE_NA_CMD.format(file=f"$ARTIFACT_DIR/{ LOCUST_FILE_PREFIX }_stats.csv"))
        os.system(REMOVE_NA_CMD.format(file=f"$ARTIFACT_DIR/{ LOCUST_FILE_PREFIX }_stats_history.csv"))
        reporter_retcode = os.system(LOCUST_REPORTER_CMD)
        if reporter_retcode != 0:
            logging.warning(f"locust-reporter failed (retcode={reporter_retcode})...")

    return test_retcode

if __name__ == "__main__":
    test_retcode = 255
    try:
        test_retcode = main()
    finally:
        logging.info("Triggering the artifact export.")
        with open(artifacts_directory / "test.exit_code", "w") as out_f:
            print(str(test_retcode), file=out_f)

    sys.exit(test_retcode)
