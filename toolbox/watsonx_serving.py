import sys

from toolbox._common import RunAnsibleRole, AnsibleRole, AnsibleMappedParams, AnsibleConstant, AnsibleSkipConfigGeneration

class Watsonx_Serving:
    """
    Commands relating to WatsonX Serving stack
    """

    @AnsibleRole("watsonx_serving_capture_state")
    @AnsibleMappedParams
    def capture_state(self, namespace=""):
        """
        Captures the state of the WatsonX serving stack in a given namespace

        Args:
          namespace: the namespace in which the Serving stack was deployed. If empty, use the current project.
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("watsonx_serving_capture_operators_state")
    @AnsibleMappedParams
    def capture_operators_state(self):
        """
        Captures the state of the operators of the WatsonX serving stack

        Args:
        """

        return RunAnsibleRole(locals())
