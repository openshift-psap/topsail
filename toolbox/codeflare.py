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
        """

        return RunAnsibleRole(locals())
