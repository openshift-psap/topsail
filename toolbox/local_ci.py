import datetime
import logging
import sys

from toolbox._common import RunAnsibleRole, AnsibleRole, AnsibleMappedParams, AnsibleConstant, AnsibleSkipConfigGeneration

class Local_CI:
    """
    Commands to run the CI scripts in a container environment similar to the one used by the CI
    """

    @AnsibleRole("local_ci_run")
    @AnsibleMappedParams
    def run(self, ci_command,
            pr_number=None,
            git_repo="https://github.com/openshift-psap/ci-artifacts",
            git_ref="main",
            namespace="ci-artifacts",
            istag="ci-artifacts:main",
            pod_name="ci-artifacts",
            service_account="default",
            secret_name=None,
            secret_env_key=None,
            test_name="local-ci-test",
            test_args=[],
            init_command=None,
            export_bucket_name=None,
            export_test_run_identifier="default",
            export=True,
            retrieve_artifacts=True,
            pr_config=None,
            update_git=True,
            ):
        """
        Runs a given CI command

        Args:
            git_repo: The Github repo to use.
            git_ref: The Github ref to use.
            pr_number: The ID of the PR to use for the repository.
            ci_command: The CI command to run.
            namespace: The namespace in which the image.
            istag: The imagestream tag to use.
            pod_name: The name to give to the Pod running the CI command.
            service_account: Name of the ServiceAccount to use for running the Pod.
            secret_name: Name of the Secret to mount in the Pod.
            secret_env_key: Name of the environment variable with which the secret path will be exposed in the Pod.
            test_name: Name of the test being executed.
            test_args: List of arguments to give to the test.
            init_command: Command to run in the container before running anything else.
            export_bucket_name: Name of the S3 bucket where the artifacts should be exported.
            export_test_run_identifier: Identifier of the test being executed (will be a dirname).
            export: If True, exports the artifacts to the S3 bucket. If False, do not run the export command.
            retrieve_artifacts: If False, do not retrieve locally the test artifacts.
            pr_config: Optional path to a PR config file (avoids fetching Github PR json).
            update_git: If True, updates the git repo with the latest main/PR before running the test.
        """

        if pr_number and not update_git:
            logging.error(f"Cannot have --pr-number={pr_number} without --update-git")
            sys.exit(1)

        if export and not export_bucket_name:
            logging.error("Cannot have --export without --export-bucket-name")
            sys.exit(1)

        return RunAnsibleRole(locals())

    @AnsibleRole("local_ci_run_multi")
    @AnsibleMappedParams
    def run_multi(self, ci_command,
                  user_count: int = 1,
                  namespace="ci-artifacts",
                  istag="ci-artifacts:main",
                  job_name="ci-artifacts",
                  service_account="default",
                  secret_name=None,
                  secret_env_key=None,
                  retrieve_artifacts=False,
                  minio_namespace=None,
                  minio_bucket_name=None,
                  minio_secret_key_key=None,
                  variable_overrides=None,
                  use_local_config=True,
                  capture_prom_db: bool = True,
                  git_pull: bool = False,
                  state_signal_redis_server=None,
                  sleep_factor=0.0,
                  user_batch_size=1,
                  abort_on_failure=False,
                  need_all_success=False,
                  ):
        """
        Runs a given CI command in parallel from multiple Pods

        Args:
            ci_command: The CI command to run.
            user_count: Batch job parallelism count.
            namespace: The namespace in which the image.
            istag: The imagestream tag to use.
            job_name: The name to give to the Job running the CI command.
            service_account: Name of the ServiceAccount to use for running the Pod.
            secret_name: Name of the Secret to mount in the Pod.
            secret_env_key: Name of the environment variable with which the secret path will be exposed in the Pod.
            retrieve_artifacts: If False, do not retrieve locally the test artifacts.
            minio_namespace: Namespace where the Minio server is located.
            minio_bucket_name: Name of the bucket in the Minio server.
            minio_secret_key_key: Key inside 'secret_env_key' containing the secret to access the Minio bucket. Must be in the form 'user_password=SECRET_KEY'.
            variable_overrides: Optional path to the variable_overrides config file (avoids fetching Github PR json).
            use_local_config: If true, gives the local configuration file ($CI_ARTIFACTS_FROM_CONFIG_FILE) to the Pods.
            capture_prom_db: If True, captures the Prometheus DB of the systems.
            git_pull: If True, update the repo in the image with the latest version of the build ref before running the command in the Pods.
            state_signal_redis_server: Optional address of the Redis server to pass to StateSignal synchronization.
            sleep_factor: Delay (in seconds) between the start of each of the users.
            user_batch_size: Number of users to launch after the sleep delay.
            abort_on_failure: If true, let the Job abort the parallel execution on the first Pod failure. If false, ignore the process failure and track the overall failure count with a flag.
            need_all_success: if true, fails the execution if any of the Pods failed. If false, fails it if none of the Pods succeed.
        """

        if retrieve_artifacts and not (minio_namespace and minio_bucket_name):
            logging.error(f"--minio_namespace and --minio_bucket_name must be provided when --retrieve_artifacts is enabled")
            sys.exit(1)

        return RunAnsibleRole(locals())
