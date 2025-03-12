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
        Runs a model with ollama, on a remote host

        Args:
          base_work_dir: the base directory where to store things
          path: the path to the ollama binary
          name: the name of the model to fetch
          unload: if True, unloads (stops serving) this model
        """

        return RunAnsibleRole(locals())


    @AnsibleRole("mac_ai_remote_llama_cpp_run_model")
    @AnsibleMappedParams
    def remote_llama_cpp_run_model(
            self,
            base_work_dir,
            path,
            port,
            name,
            prefix="",
            ngl=99,
    ):
        """
        Runs a model with llama_cpp, on a remote host

        Args:
          base_work_dir: the base directory where to store things
          prefix: the prefix to get the llama-server running
          path: the path to the llama-server binary
          port: the port number on which llama-cpp should listen
          name: the name of the model to fetch
          ngl: number of layers to store in VRAM
        """

        return RunAnsibleRole(locals())


    @AnsibleRole("mac_ai_remote_llama_cpp_pull_model")
    @AnsibleMappedParams
    def remote_llama_cpp_pull_model(
            self,
            base_work_dir,
            path,
            name,
            dest=None,
    ):
        """
        Pulls a model with llama-cpp, on a remote host

        Args:
          base_work_dir: the base directory where to store things
          path: the path to the llama-cpp binary
          name: the name of the model to fetch
          dest: if specified, where to put the model being pulled
        """

        return RunAnsibleRole(locals())


    @AnsibleRole("mac_ai_remote_capture_power_usage")
    @AnsibleMappedParams
    def remote_capture_power_usage(
            self,
            samplers="gpu_power",
            sample_rate=1000,
            stop=False,
    ):
        """
        Captures the power usage on MacOS

        Args:
          samplers: name(s) of the source sample to capture
          sample_rate: rate at which the metrics should be captured, in ms
          stop: if true, only stop the capture
        """

        return RunAnsibleRole(locals())


    @AnsibleRole("mac_ai_remote_capture_cpu_ram_usage")
    @AnsibleMappedParams
    def remote_capture_cpu_ram_usage(
            self,
            stop=False,
    ):
        """
        Captures the CPU and RAM usage on MacOS

        Args:
          stop: if true, only stop the capture
        """

        return RunAnsibleRole(locals())


    @AnsibleRole("mac_ai_remote_capture_virtgpu_memory")
    @AnsibleMappedParams
    def remote_capture_virtgpu_memory(
            self,
            podman_machine_ssh_cmd,
            stop=False,
    ):
        """
        Captures the virt-gpu memory usage

        Args:
          podman_machine_ssh_cmd: the command to execute to enter the VM host
          stop: if true, only stop the capture
        """

        return RunAnsibleRole(locals())


    @AnsibleRole("mac_ai_remote_capture_system_state")
    @AnsibleMappedParams
    def remote_capture_system_state(
            self,
    ):
        """
        Captures the state of the remote Mac system

        Args:
        """

        return RunAnsibleRole(locals())
