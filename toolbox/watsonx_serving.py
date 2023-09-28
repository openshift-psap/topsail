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
                     model_name,
                     model_id,
                     serving_runtime_name, serving_runtime_image, serving_runtime_resource_request,
                     inference_service_name,
                     storage_uri,
                     sa_name,
                     inference_service_min_replicas : int = None,
                     secret_env_file_name=None,
                     secret_env_file_key=None,
                     env_extra_values : dict = {},
                     query_data=None,
                     mute_serving_logs=False,
                     delete_others=True,
                     ):
        """
        Deploy a WatsonX-Serving model

        Args:
          name: the name of the resource to create
          namespace: the namespace in which the model should be deployed
          model_name: the full name of the model
          model_id: the ID of the model, for the validation step

          serving_runtime_name: the name to give to the serving runtime
          serving_runtime_image: the image of the serving runtime
          serving_runtime_resource_request: the resource request of the serving runtime

          inference_service_name: the name to give to the inference service
          inference_service_min_replicas: the minimum number of replicas. If none, the field is left unset.
          sa_name: name of the service account to use for running the Pod
          storage_uri: [S3] URI where the model is stored

          secret_env_file_name: name of the YAML file containing the secret environment key/values
          secret_env_file_key: key to the secret environment key/values in the secret file
          env_extra_values: extra key/value pairs (will override the values from the secret file)

          query_data: a JSON payload used to validate the model deployment

          mute_serving_logs: if True, mute the serving runtime container logs

          delete_others: if True, deletes the other serving runtime/inference services of the namespace
        """

        return RunAnsibleRole(locals())



    @AnsibleRole("watsonx_serving_validate_model")
    @AnsibleMappedParams
    def validate_model(self,
                       inference_service_names,
                       model_id,
                       query_data,
                       namespace=""):
        """
        Validate the proper deployment of a WatsonX model

        Warning:
          This command requires `grpcurl` to be available in the PATH.

        Args:
          inference_service_names: a list of names of the inference service to validate
          model_id: the model-id to pass to the inference service
          query_data: the data to pass to the model query
          namespace: the namespace in which the Serving stack was deployed. If empty, use the current project.
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
