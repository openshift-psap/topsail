from projects.core.library.ansible_toolbox import (
    RunAnsibleRole, AnsibleRole,
    AnsibleMappedParams
)


class Container_Bench:
    """
    Commands relating to the performance evaluation
    """

    @AnsibleRole("container_bench_sysbench_cpu_benchmark")
    @AnsibleMappedParams
    def sysbench_cpu_benchmark(
            self,
            exec_time_path,
            binary_path,
            rootfull=False,
            additional_args="",
    ):
        """
        Runs the sysbench CPU benchmark with the given runtime
        Args:
          exec_time_path: path to the exec_time.py script
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_sysbench_memory_read_benchmark")
    @AnsibleMappedParams
    def sysbench_memory_read_benchmark(
            self,
            exec_time_path,
            binary_path,
            rootfull=False,
            additional_args="",
    ):
        """
        Runs the sysbench memory read benchmark with the given runtime
        Args:
          exec_time_path: path to the exec_time.py script
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_sysbench_memory_write_benchmark")
    @AnsibleMappedParams
    def sysbench_memory_write_benchmark(
            self,
            exec_time_path,
            binary_path,
            rootfull=False,
            additional_args="",
    ):
        """
        Runs the sysbench memory write benchmark with the given runtime
        Args:
          exec_time_path: path to the exec_time.py script
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_sysbench_fileio_container_benchmark")
    @AnsibleMappedParams
    def sysbench_fileio_container_benchmark(
            self,
            exec_time_path,
            binary_path,
            rootfull=False,
            additional_args="",
    ):
        """
        Runs the sysbench fileIO container benchmark with the given runtime
        Args:
          exec_time_path: path to the exec_time.py script
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_sysbench_fileio_mount_benchmark")
    @AnsibleMappedParams
    def sysbench_fileio_mount_benchmark(
            self,
            exec_time_path,
            binary_path,
            rootfull=False,
            additional_args="",
    ):
        """
        Runs the sysbench fileIO mount benchmark with the given runtime
        Args:
          exec_time_path: path to the exec_time.py script
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_iperf_net_bridge_benchmark")
    @AnsibleMappedParams
    def iperf_net_bridge_benchmark(
            self,
            exec_time_path,
            binary_path,
            rootfull=False,
            additional_args="",
    ):
        """
        Runs the iperf3 benchmark using network bridge between containers with the given runtime
        Args:
          exec_time_path: path to the exec_time.py script
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_iperf_net_host_benchmark")
    @AnsibleMappedParams
    def iperf_net_host_benchmark(
            self,
            exec_time_path,
            binary_path,
            rootfull=False,
            additional_args="",
    ):
        """
        Runs the iperf3 benchmark using network host network between containers with the given runtime
        Args:
          exec_time_path: path to the exec_time.py script
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_iperf_host_to_container_benchmark")
    @AnsibleMappedParams
    def iperf_host_to_container_benchmark(
            self,
            exec_time_path,
            binary_path,
            rootfull=False,
            additional_args="",
    ):
        """
        Runs the iperf3 benchmark using from host to container with the given runtime
        Args:
          exec_time_path: path to the exec_time.py script
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_artifact_add_benchmark")
    @AnsibleMappedParams
    def artifact_add_benchmark(
            self,
            exec_time_path,
            binary_path,
            rootfull=False,
            additional_args="",
    ):
        """
        Runs the artifact add benchmark with the given runtime
        Args:
          exec_time_path: path to the exec_time.py script
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_helloworld_benchmark")
    @AnsibleMappedParams
    def helloworld_benchmark(
            self,
            exec_time_path,
            binary_path,
            rootfull=False,
            additional_args="",
    ):
        """
        Runs the helloworld benchmark with the given runtime
        Args:
          exec_time_path: path to the exec_time.py script
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_exec_benchmark")
    @AnsibleMappedParams
    def exec_benchmark(
            self,
            exec_time_path,
            binary_path,
            rootfull=False,
            additional_args="",
    ):
        """
        Runs the exec benchmark with the given runtime
        Args:
          exec_time_path: path to the exec_time.py script
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_image_build_large_build_context_benchmark")
    @AnsibleMappedParams
    def image_build_large_build_context_benchmark(
            self,
            exec_time_path,
            binary_path,
            rootfull=False,
            additional_args="",
    ):
        """
        Runs the image build large build context benchmark with the given runtime
        Args:
          exec_time_path: path to the exec_time.py script
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
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
            binary_path,
            rootfull=False,
            additional_args="",
    ):
        """
        Captures the info of the container engine
        Args:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
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
