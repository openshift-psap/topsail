import sys

from projects.core.library.ansible_toolbox import (
    RunAnsibleRole, AnsibleRole,
    AnsibleMappedParams, AnsibleConstant,
    AnsibleSkipConfigGeneration
)

class Scheduler:
    """
    Commands relating to RHOAI scheduler testing
    """

    @AnsibleRole("scheduler_generate_load")
    @AnsibleMappedParams
    def generate_load(
            self,
            namespace,
            base_name="sched-test-",
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
            scheduler_load_generator="projects/scheduler/subprojects/scheduler-load-generator/generator.py",
            kueue_queue="local-queue",
    ):
        """
        Generate scheduler load

        Args:
          namespace: name of the namespace where the scheduler load will be generated
          base_name: name prefix for the scheduler resources
          count: number of resources to create
          job_template_name: name of the job template to use inside the AppWrapper
          mode: mcad, kueue, coscheduling or job
          pod_count: number of Pods to create in each of the AppWrappers
          pod_runtime: run time parameter to pass to the Pod
          pod_requests: requests to pass to the Pod definition
          states_target: list of expected target states
          states_unexpected: list of states that fail the test
          timespan: number of minutes over which the resources should be created
          distribution: the distribution method to use to spread the resource creation over the requested timespan
          scheduler_load_generator: the path of the scheduler load generator to launch
          kueue_queue: the name of the Kueue queue to use
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("scheduler_cleanup")
    @AnsibleMappedParams
    def cleanup(self,
                namespace
                ):
        """
        Clean up the scheduler load namespace

        Args:
          namespace: name of the namespace where the scheduler load was generated
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("scheduler_deploy_mcad_from_helm")
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

    @AnsibleRole("scheduler_create_mcad_canary")
    @AnsibleMappedParams
    def create_mcad_canary(self,
                namespace
                ):
        """
        Create a canary for MCAD Appwrappers and track the time it takes to be scheduled

        Args:
          namespace: name of the namespace where the canary should be generated
        """

        return RunAnsibleRole(locals())
