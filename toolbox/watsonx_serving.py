import sys

from toolbox._common import RunAnsibleRole, AnsibleRole, AnsibleMappedParams, AnsibleConstant, AnsibleSkipConfigGeneration

class Watsonx_Serving:
    """
    Commands relating to WatsonX Serving stack
    """

    @AnsibleRole("watsonx_serving_deploy_model")
    @AnsibleMappedParams
    def deploy_model(self,
                     namespace,
                     serving_runtime_name, serving_runtime_image, serving_runtime_resource_request,
                     inference_service_name,
                     storage_uri,
                     sa_name):
        """
        Deploy a WatsonX-Serving model

        Args:
          name: the name of the resource to create
          namespace: the namespace in which the model should be deployed

          serving_runtime_name: the name to give to the serving runtime
          serving_runtime_image: the image of the serving runtime
          serving_runtime_resource_request: the resource request of the serving runtime

          inference_service_name: the name to give to the inference service

          sa_name: name of the service account to use for running the Pod
          storage_uri: [S3] URI where the model is stored
        """

        return RunAnsibleRole(locals())


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
