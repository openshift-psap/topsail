import sys

from toolbox._common import RunAnsibleRole, AnsibleRole, AnsibleMappedParams, AnsibleConstant, AnsibleSkipConfigGeneration

from toolbox import local_ci


class Pipelines:
    """
    Commands relating to RHODS
    """

    @AnsibleRole("pipelines_deploy_application")
    @AnsibleMappedParams
    def deploy_application(self, name, namespace, secret_properties_file):
        """
        Deploy a Data Science Pipeline Application in a given namespace.

        Args:
          name: the name of the application to deploy
          namespace: the namespace in which the application should be deployed
          secret_properties_file: Path of a file containing the properties of LDAP secrets. (See 'cluster deploy_ldap' command)
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("pipelines_run_kfp_notebook")
    @AnsibleMappedParams
    def run_kfp_notebook(self,
                         namespace="",
                         dsp_application_name="",
                         imagestream="s2i-generic-data-science-notebook",
                         imagestream_tag="",
                         notebook_directory="testing/pipelines/notebooks/hello-world",
                         notebook_filename="kfp_hello_world.ipynb",
                         stop_on_exit=True,
                         capture_artifacts=True,
                         capture_prom_db=False,
                         ):
        """
        Run a notebook in a given notebook image.

        Args:
          namespace: Namespace in which the notebook will be deployed, if not deploying with RHODS. If empty, use the project return by 'oc project --short'.
          dsp_application_name: The name of the DSPipelines Application to use. If empty, lookup the application name in the namespace.
          imagestream: Imagestream to use to look up the notebook Pod image.
          imagestream_tag: Imagestream tag to use to look up the notebook Pod image. If emtpy and and the image stream has only one tag, use it. Fails otherwise.
          notebook_directory: Directory containing the files to mount in the notebook.
          notebook_filename: Name of the ipynb notebook file to execute with JupyterLab.
          stop_on_exit: If False, keep the notebook running after the test.
          capture_artifacts: If False, disable the post-test artifact collection.
          capture_prom_db: If True, captures the Prometheus DB of the systems.
        """

        return RunAnsibleRole(locals())


    @AnsibleRole("pipelines_capture_state")
    @AnsibleMappedParams
    def capture_state(self, dsp_application_name="", namespace=""):
        """
        Captures the state of a Data Science Pipeline Application in a given namespace.

        Args:
          dsp_application_name: the name of the application
          namespace: the namespace in which the application was deployed
        """

        return RunAnsibleRole(locals())
