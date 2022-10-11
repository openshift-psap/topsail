import time
import datetime
import os, sys
import pathlib
import tarfile

LOCUST_TEST_CMD = "cd $LOCUST_DIR; PYTHONUNBUFFERED=1 locust --headless \
    --csv $ARTIFACT_DIR/api_scale_test \
    --csv-full-history \
    --html $ARTIFACT_DIR/api_scale_test.html \
    --only-summary \
"

LOCUST_REPORTER_CMD = "locust-reporter \
    -prefix $ARTIFACT_DIR/api_scale_test \
    -failures=true \
    -outfile $ARTIFACT_DIR/locust_reporter.html \
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

    print(f"Running locust test: {api_scale_test_name}")
    print(f"Against RHODS {rhods_dashboard} version {rhods_version}")
    print(f"Connect with user {username_prefix}|{job_completion_index} on {idp_name}")

    print(f"Storing artifacts in {artifacts_directory}")
    artifacts_directory.mkdir(parents=True, exist_ok=True)

    print(LOCUST_TEST_CMD)
    test_retcode = os.system(LOCUST_TEST_CMD) != 0

    if test_retcode: return test_retcode

    if not os.system(LOCUST_REPORTER_CMD):
        print("WARNING: locust-reporter failed ...")

    return 0

if __name__ == "__main__":
    test_retcode = 255
    try:
        test_retcode = main()
    finally:
        print("Triggering the artifact export.")
        with open(artifacts_directory / "test.exit_code", "w") as out_f:
            print(str(test_retcode), file=out_f)

    sys.exit(test_retcode)
