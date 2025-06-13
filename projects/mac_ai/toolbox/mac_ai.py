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
            port,
            stop=False
    ):
        """
        Starts ollama, on a remote host

        Args:
          base_work_dir: the base directory where to store things
          path: the path to the ollama binary
          port: the port on which the server should listen
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
          name: the name of the model to run
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
          name: the name of the model to run
          ngl: number of layers to store in VRAM
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("mac_ai_remote_llama_cpp_run_bench")
    @AnsibleMappedParams
    def remote_llama_cpp_run_bench(
            self,
            path,
            model_name,
            prefix="",
            ngl=99,
            verbose=True,
            llama_bench=True,
            test_backend_ops=True,
    ):
        """
        Benchmark a model with llama_cpp, on a remote host

        Args:
          prefix: the prefix to get the llama.cpp binaries running
          path: the path to the llama.cpp bin directory
          port: the port number on which llama-cpp should listen
          model_name: the name of the model to use
          ngl: number of layers to store in VRAM
          verbose: if true, runs the benchmark in verbose mode

          llama_bench: if true, runs the llama-bench benchmark
          test_backend_ops: if true, runs the test-backend-ops benchmark
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

    @AnsibleRole("mac_ai_remote_ramalama_run_model")
    @AnsibleMappedParams
    def remote_ramalama_run_model(
            self,
            base_work_dir,
            path,
            port,
            model_name,
            env,
            ngl=99,
            device=None,
            unload=False,
            image="quay.io/ramalama/ramalama:latest",
    ):
        """
        Runs a model with ramalama, on a remote host

        Args:
          base_work_dir: the base directory where to store things
          path: the path to the llama-server binary
          pythonpath: the value to pass as PYTHONPATH
          port: the port number on which llama-cpp should listen
          model_name: the name of the model to run
          env: the env values to set before running ramalama
          ngl: number of layers to store in VRAM
          device: name of the device to pass to the container
          unload: if True, unloads (stops serving) this model
          image: the image to use to run ramalama
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("mac_ai_remote_ramalama_run_bench")
    @AnsibleMappedParams
    def remote_ramalama_run_bench(
            self,
            base_work_dir,
            path,
            model_name,
            env,
            ngl=99,
            device=None,
            image="quay.io/ramalama/ramalama:latest",
    ):
        """
        Benchmark a model with ramalama, on a remote host

        Args:
          base_work_dir: the base directory where to store things
          path: the path to the llama.cpp bin directory
          model_name: the name of the model to use
          env: the env values to set before running ramalama
          ngl: number of layers to store in VRAM
          device: name of the device to pass to the container
          image: the image to use to run ramalama
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

    @AnsibleRole("mac_ai_remote_build_virglrenderer")
    @AnsibleMappedParams
    def remote_build_virglrenderer(
            self,
            source_dir,
            build_dir,
            build_flags,
    ):
        """
        Builds the Virglrenderer library

        Args:
          source_dir: the path to the source directory
          build_dir: the path to the build directory
          build_flags: the build flags to pass to meson
        """

        return RunAnsibleRole(locals())
