import datetime

from toolbox._common import RunAnsibleRole, AnsibleRole, AnsibleMappedParams, AnsibleConstant, AnsibleSkipConfigGeneration

class LocalCI:
    """
    Commands to run the CI scripts in a container environment similar to the one used by the CI
    """

    @AnsibleRole("local_ci_run")
    @AnsibleMappedParams
    def run(self, ci_command,
            pr_number=None,
            repo="https://github.com/openshift-psap/ci-artifacts",
            namespace="ci-artifacts",
            istag="ci-artifacts:main",
            pod_name="ci-artifacts",
            service_account="default",
            secret_name=None,
            secret_env_key=None,
            export_command=None,
            export_identifier="default",
            export_ts_id=None,
            export=True,
            ):
        """
        Runs a given CI command

        Args:
            repo: The Github repo to use.
            pr_number: The ID of the PR to use for the repository.
            ci_command: The CI command to run.
            namespace: The namespace in which the image.
            istag: The imagestream tag to use.
            pod_name: The name to give to the Pod running the CI command.
            service_account: Name of the ServiceAccount to use for running the Pod.
            secret_name: Name of the Secret to mount in the Pod.
            secret_env_key: Name of the environment variable with which the secret path will be exposed in the Pod.
            export_identifier: Identifier of the test being executed (will be a dirname).
            export_ts_id: Timestamp identifier of the test being executed (will be a dirname).
            export_command: Command to run to export the execution artifacts to a external storage.
            export: If False, do not run the export command.
        """

        if not export_ts_id:
            export_ts_id = datetime.datetime.now().strftime("%Y%m%d_%H%M")

        return RunAnsibleRole(locals())
