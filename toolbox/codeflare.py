import sys

from toolbox._common import RunAnsibleRole, AnsibleRole, AnsibleMappedParams, AnsibleConstant, AnsibleSkipConfigGeneration


class Codeflare:
    """
    Commands relating to the Codeflare project
    """

    @AnsibleRole("codeflare_generate_mcad_load")
    @AnsibleMappedParams
    def generate_mcad_load(self, namespace):
        """
        Generate MCAD load

        Args:
          namespace: name of the namespace where the MCAD load will be generated
        """

        return RunAnsibleRole(locals())
