import sys

from toolbox._common import RunAnsibleRole, AnsibleRole, AnsibleMappedParams, AnsibleConstant, AnsibleSkipConfigGeneration


class Codeflare:
    """
    Commands relating to the Codeflare project
    """

    @AnsibleRole("codeflare_generate_mcad_load")
    @AnsibleMappedParams
    def generate_mcad_load(self,
                           namespace,
                           aw_base_name="appwrapper",
                           job_template_name="sleeper",
                           states_target=["Completed"],
                           states_unexpected=["Failed"],
                           job_mode=False,
                           aw_count=3,
                           pod_count=1,
                           pod_runtime=30,
                           pod_requests={"cpu": "100m"},
                           timespan=0,
                           distribution="poisson",
                           mcad_namespace="opendatahub",
                           mcad_labels="app=mcad-mcad",
                           mcad_deploy="mcad-controller-mcad",
                           ):
        """
        Generate MCAD load

        Args:
          namespace: name of the namespace where the MCAD load will be generated
          aw_base_name: name prefix for the AppWrapper resources
          job_template_name: name of the job template to use inside the AppWrapper
          job_mode: if true, create Jobs instead of AppWrappers
          pod_count: number of Pods to create in each of the AppWrappers
          pod_runtime: run time parameter to pass to the Pod
          pod_requests: requests to pass to the Pod definition
          states_target: list of expected target states
          states_unexpected: list of states that fail the test
          aw_count: number of AppWrapper replicas to create
          timespan: number of minutes over which the AppWrappers should be created
          distribution: the distribution method to use to spread the resource creation over the requested timespan
          mcad_namespace: namespace where MCAD is deployed
          mcad_labels: labels to find the MCAD controller pods
          mcad_deploy: name of the MCAD controller deployment
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
