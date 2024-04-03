import sys

from topsail._common import RunAnsibleRole, AnsibleRole, AnsibleMappedParams, AnsibleConstant, AnsibleSkipConfigGeneration


class Codeflare:
    """
    Commands relating to the Codeflare project
    """

    @AnsibleRole("codeflare_generate_scheduler_load")
    @AnsibleMappedParams
    def generate_scheduler_load(
            self,
            namespace,
            base_name="appwrapper",
            job_template_name="sleeper",
            states_target=["Completed"],
            states_unexpected=["Failed"],
            mode="job",
            count=3,
            pod_count=1,
            pod_runtime=30,
            pod_requests={"cpu": "100m"},
            timespan=0,
            distribution="poisson",
            scheduler_load_generator="projects/codeflare/subprojects/scheduler-load-generator/generator.py",
    ):
        """
        Generate scheduler load

        Args:
          namespace: name of the namespace where the MCAD load will be generated
          base_name: name prefix for the AppWrapper resources
          count: number of resources to create
          job_template_name: name of the job template to use inside the AppWrapper
          mode: mcad (AppWrappers), kueue or job
          pod_count: number of Pods to create in each of the AppWrappers
          pod_runtime: run time parameter to pass to the Pod
          pod_requests: requests to pass to the Pod definition
          states_target: list of expected target states
          states_unexpected: list of states that fail the test
          timespan: number of minutes over which the AppWrappers should be created
          distribution: the distribution method to use to spread the resource creation over the requested timespan
          scheduler_load_generator: the path of the scheduler load generator to launch
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("codeflare_cleanup_appwrappers")
    @AnsibleMappedParams
    def cleanup_appwrappers(self,
                            namespace
                            ):
        """
        Clean up the AppWrappers and track MCAD recovery time

        Args:
          namespace: name of the namespace where the AppWrappers are deployed
        """

        return RunAnsibleRole(locals())


    @AnsibleRole("codeflare_capture_state")
    @AnsibleMappedParams
    def capture_state(self,
                            namespace
                            ):
        """
        Capture the state of the codeflare stack

        Args:
          namespace: name of the namespace where the Codeflare stack ran
        """

        return RunAnsibleRole(locals())


    @AnsibleRole("codeflare_deploy_mcad_from_helm")
    @AnsibleMappedParams
    def deploy_mcad_from_helm(
            self,
            namespace,
            git_repo="https://github.com/project-codeflare/multi-cluster-app-dispatcher",
            git_ref="main",
            image_repo="quay.io/project-codeflare/mcad-controller",
            image_tag="stable",
    ):
        """
        Deploys MCAD from helm

        Args:
          namespace: name of the namespace where MCAD should be deployed
          git_repo: name of the GIT repo to clone
          git_ref: name of the GIT branch to fetch
          image_repo: name of the image registry where the image is stored
          image_tag: tag of the image to use
        """

        return RunAnsibleRole(locals())
