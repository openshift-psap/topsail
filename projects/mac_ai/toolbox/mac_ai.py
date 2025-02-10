import sys

from projects.core.library.ansible_toolbox import (
    RunAnsibleRole, AnsibleRole,
    AnsibleMappedParams, AnsibleConstant,
    AnsibleSkipConfigGeneration
)

class Mac_Ai:
    """
    Commands relating to the MacOS AI performance evaluation
    """

    @AnsibleRole("mac_ai_remote_ollama_start")
    @AnsibleMappedParams
    def remote_ollama_start(
            self,
            base_work_dir,
            path,
            stop=False
    ):
        """
        Starts ollama, on a remote host

        Args:
          base_work_dir: the base directory where to store things
          path: the path to the ollama binary
          stop: if true, stop the server instead of starting it
        """

        return RunAnsibleRole(locals())


    @AnsibleRole("mac_ai_remote_ollama_pull_model")
    @AnsibleMappedParams
    def remote_ollama_pull_model(
            self,
            base_work_dir,
            path,
            name,
    ):
        """
        Pulls a model with ollama, on a remote host

        Args:
          base_work_dir: the base directory where to store things
          path: the path to the ollama binary
          name: the name of the model to fetch
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("mac_ai_remote_ollama_run_model")
    @AnsibleMappedParams
    def remote_ollama_run_model(
            self,
            base_work_dir,
            path,
            name,
            unload=False,
    ):
        """
        Pulls a model with ollama, on a remote host

        Args:
          base_work_dir: the base directory where to store things
          path: the path to the ollama binary
          name: the name of the model to fetch
          unload: if True, unloads (stops serving) this model
        """

        return RunAnsibleRole(locals())
