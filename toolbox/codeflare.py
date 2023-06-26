import sys

from toolbox._common import RunAnsibleRole, AnsibleRole, AnsibleMappedParams, AnsibleConstant, AnsibleSkipConfigGeneration


class Codeflare:
    """
    Commands relating to the Codeflare project
    """

    @AnsibleRole("codeflare_generate_mcad_load")
    @AnsibleMappedParams
    def generate_mcad_load(self, namespace,
                           target_states=["Completed"],
                           fail_if_states=["Failed"],
                           job_mode=False,
                           ):
        """
        Generate MCAD load

        Args:
          namespace: name of the namespace where the MCAD load will be generated
          target_states: list of expected target states
          fail_if_states: list of states that fail the test
          job_mode: if true, create Jobs instead of AppWrappers
        """

        return RunAnsibleRole(locals())
