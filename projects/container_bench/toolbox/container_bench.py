from projects.core.library.ansible_toolbox import (
    RunAnsibleRole, AnsibleRole,
    AnsibleMappedParams
)


class Container_Bench:
    """
    Commands relating to the performance evaluation
    """

    @AnsibleRole("container_bench_helloworld_benchmark")
    @AnsibleMappedParams
    def helloworld_benchmark(
            self,
            exec_time_path,
            runtime,
    ):
        """
        Runs the helloworld benchmark with the given runtime
        Args:
          exec_time_path: path to the exec_time.py script
          runtime: the runtime to use for the benchmark (e.g., docker, podman)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_exec_benchmark")
    @AnsibleMappedParams
    def exec_benchmark(
            self,
            exec_time_path,
            runtime,
    ):
        """
        Runs the exec benchmark with the given runtime
        Args:
          exec_time_path: path to the exec_time.py script
          runtime: the runtime to use for the benchmark (e.g., docker, podman)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_image_build_large_build_context_benchmark")
    @AnsibleMappedParams
    def image_build_large_build_context_benchmark(
            self,
            exec_time_path,
            runtime,
    ):
        """
        Runs the image build large build context benchmark with the given runtime
        Args:
          exec_time_path: path to the exec_time.py script
          runtime: the runtime to use for the benchmark (e.g., docker, podman)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_capture_system_state")
    @AnsibleMappedParams
    def capture_system_state(
            self,
    ):
        """
        Captures the state of the remote Mac system

        Args:
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_capture_container_engine_info")
    @AnsibleMappedParams
    def capture_container_engine_info(
            self,
            runtime
    ):
        """
        Captures the info of the container engine
        Args:
          runtime: the container engine to capture information from (e.g., podman, docker)
        """

        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_prepare_benchmark_script_on_remote")
    @AnsibleMappedParams
    def prepare_benchmark_script_on_remote(
            self,
            source,
            dest,
    ):
        """
        Prepares the benchmark script on the remote machine
        Args:
          source: the source file to copy
          dest: the destination path on the remote machine
        """
        return RunAnsibleRole(locals())
