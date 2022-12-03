import time
import datetime
import os, sys
import pathlib
import tarfile
import logging
logging.getLogger().setLevel(logging.INFO)

LOCUST_FILE_PREFIX="locust_scale_test"

LOCUST_TEST_CMD = f"cd $LOCUST_DIR; PYTHONUNBUFFERED=1 locust --headless \
    --csv $ARTIFACT_DIR/{ LOCUST_FILE_PREFIX } \
    --csv-full-history \
    --html $ARTIFACT_DIR/{ LOCUST_FILE_PREFIX }.html \
    --only-summary \
     > $ARTIFACT_DIR/{ LOCUST_FILE_PREFIX }.stdout \
    2> $ARTIFACT_DIR/{ LOCUST_FILE_PREFIX }.stderr \
"

LOCUST_REPORTER_CMD = f"locust-reporter \
    -prefix $ARTIFACT_DIR/{ LOCUST_FILE_PREFIX } \
    -failures=true \
    -outfile $ARTIFACT_DIR/{LOCUST_FILE_PREFIX}_report.html \
"

artifacts_directory = pathlib.Path(os.getenv("ARTIFACT_DIR"))

def main():
    api_scale_test_name = os.getenv("API_SCALE_TEST_NAME")

    rhods_dashboard = os.getenv("ODH_DASHBOARD_URL")
    rhods_version = os.getenv("RHODS_VERSION")

    username_prefix = os.getenv("TEST_USERS_USERNAME_PREFIX")
    job_completion_index = os.getenv("JOB_COMPLETION_INDEX", 0)
    idp_name = os.getenv("TEST_USERS_IDP_NAME")
    creds_file = os.getenv("CREDS_FILE")

    logging.info(f"Running locust test: {api_scale_test_name}")
    logging.info(f"Against RHODS {rhods_dashboard} version {rhods_version}")
    logging.info(f"Connect with user {username_prefix}|{job_completion_index} on {idp_name}")

    logging.info(f"Storing artifacts in {artifacts_directory}")
    artifacts_directory.mkdir(parents=True, exist_ok=True)

    logging.info(LOCUST_TEST_CMD)
    test_retcode = os.system(LOCUST_TEST_CMD)

    if not test_retcode:
        logging.error("locust failed ...")

    if not os.system(LOCUST_REPORTER_CMD):
        logging.error("locust-reporter failed ...")

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
