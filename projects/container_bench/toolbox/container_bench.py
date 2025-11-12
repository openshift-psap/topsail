from projects.core.library.ansible_toolbox import (
    RunAnsibleRole, AnsibleRole,
    AnsibleMappedParams
)


class Container_Bench:
    """
    Commands relating to the performance evaluation
    """

    @AnsibleRole("container_bench_create_container_benchmark")
    @AnsibleMappedParams
    def create_container_benchmark(
            self,
            exec_props
    ):
        """
        Runs the create benchmark with the given runtime
        properties of exec_props:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
          exec_time_path: path to the exec_time.py script

        Args:
          exec_props: dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_start_container_benchmark")
    @AnsibleMappedParams
    def start_container_benchmark(
            self,
            exec_props
    ):
        """
        Runs the start benchmark with the given runtime
        properties of exec_props:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
          exec_time_path: path to the exec_time.py script

        Args:
          exec_props: dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_remove_container_benchmark")
    @AnsibleMappedParams
    def remove_container_benchmark(
            self,
            exec_props
    ):
        """
        Runs the remove container benchmark with the given runtime
        properties of exec_props:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
          exec_time_path: path to the exec_time.py script

        Args:
          exec_props: dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_pull_image_benchmark")
    @AnsibleMappedParams
    def pull_image_benchmark(
            self,
            exec_props
    ):
        """
        Runs the pull image benchmark with the given runtime
        properties of exec_props:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
          exec_time_path: path to the exec_time.py script

        Args:
          exec_props: dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_list_images_benchmark")
    @AnsibleMappedParams
    def list_images_benchmark(
            self,
            exec_props
    ):
        """
        Runs the list images benchmark with the given runtime
        properties of exec_props:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
          exec_time_path: path to the exec_time.py script

        Args:
          exec_props: dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_remove_image_benchmark")
    @AnsibleMappedParams
    def remove_image_benchmark(
            self,
            exec_props
    ):
        """
        Runs the remove image benchmark with the given runtime
        properties of exec_props:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
          exec_time_path: path to the exec_time.py script

        Args:
          exec_props: dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_commit_container_benchmark")
    @AnsibleMappedParams
    def commit_container_benchmark(
            self,
            exec_props
    ):
        """
        Runs the commit container benchmark with the given runtime
        properties of exec_props:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
          exec_time_path: path to the exec_time.py script

        Args:
          exec_props: dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_load_image_benchmark")
    @AnsibleMappedParams
    def load_image_benchmark(
            self,
            exec_props
    ):
        """
        Runs the load image benchmark with the given runtime
        properties of exec_props:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
          exec_time_path: path to the exec_time.py script

        Args:
          exec_props: dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_save_image_benchmark")
    @AnsibleMappedParams
    def save_image_benchmark(
            self,
            exec_props
    ):
        """
        Runs the save image benchmark with the given runtime
        properties of exec_props:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
          exec_time_path: path to the exec_time.py script

        Args:
          exec_props: dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_parallel_remove_image_benchmark")
    @AnsibleMappedParams
    def parallel_remove_image_benchmark(
            self,
            exec_props
    ):
        """
        Runs the parallel remove image benchmark with the given runtime
        properties of exec_props:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
          exec_time_path: path to the exec_time.py script

        Args:
          exec_props: dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_sysbench_cpu_benchmark")
    @AnsibleMappedParams
    def sysbench_cpu_benchmark(
            self,
            exec_props
    ):
        """
        Runs the sysbench CPU benchmark with the given runtime
        properties of exec_props:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
          exec_time_path: path to the exec_time.py script

        Args:
          exec_props: dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_sysbench_memory_read_benchmark")
    @AnsibleMappedParams
    def sysbench_memory_read_benchmark(
            self,
            exec_props
    ):
        """
        Runs the sysbench memory read benchmark with the given runtime
        properties of exec_props:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
          exec_time_path: path to the exec_time.py script

        Args:
          exec_props: dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_sysbench_memory_write_benchmark")
    @AnsibleMappedParams
    def sysbench_memory_write_benchmark(
            self,
            exec_props
    ):
        """
        Runs the sysbench memory write benchmark with the given runtime
        properties of exec_props:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
          exec_time_path: path to the exec_time.py script

        Args:
          exec_props: dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_sysbench_fileio_container_benchmark")
    @AnsibleMappedParams
    def sysbench_fileio_container_benchmark(
            self,
            exec_props
    ):
        """
        Runs the sysbench fileIO container benchmark with the given runtime
        properties of exec_props:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
          exec_time_path: path to the exec_time.py script

        Args:
          exec_props: dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_sysbench_fileio_mount_benchmark")
    @AnsibleMappedParams
    def sysbench_fileio_mount_benchmark(
            self,
            exec_props
    ):
        """
        Runs the sysbench fileIO mount benchmark with the given runtime
        properties of exec_props:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
          exec_time_path: path to the exec_time.py script

        Args:
          exec_props: dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_iperf_net_bridge_benchmark")
    @AnsibleMappedParams
    def iperf_net_bridge_benchmark(
            self,
            exec_props
    ):
        """
        Runs the iperf3 benchmark using network bridge between containers with the given runtime
        properties of exec_props:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
          exec_time_path: path to the exec_time.py script

        Args:
          exec_props: dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_iperf_net_host_benchmark")
    @AnsibleMappedParams
    def iperf_net_host_benchmark(
            self,
            exec_props
    ):
        """
        Runs the iperf3 benchmark using host network between containers with the given runtime
        properties of exec_props:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
          exec_time_path: path to the exec_time.py script

        Args:
          exec_props: dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_iperf_host_to_container_benchmark")
    @AnsibleMappedParams
    def iperf_host_to_container_benchmark(
            self,
            exec_props
    ):
        """
        Runs the iperf3 benchmark from host to container with the given runtime
        properties of exec_props:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
          exec_time_path: path to the exec_time.py script

        Args:
          exec_props: dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_artifact_add_benchmark")
    @AnsibleMappedParams
    def artifact_add_benchmark(
            self,
            exec_props
    ):
        """
        Runs the artifact add benchmark with the given runtime
        properties of exec_props:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
          exec_time_path: path to the exec_time.py script

        Args:
          exec_props: dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_run_container_benchmark")
    @AnsibleMappedParams
    def run_container_benchmark(
            self,
            exec_props
    ):
        """
        Runs the run container benchmark with the given runtime
        properties of exec_props:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
          exec_time_path: path to the exec_time.py script

        Args:
          exec_props: dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_exec_container_benchmark")
    @AnsibleMappedParams
    def exec_container_benchmark(
            self,
            exec_props
    ):
        """
        Runs the exec container benchmark with the given runtime
        properties of exec_props:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
          exec_time_path: path to the exec_time.py script

        Args:
          exec_props: dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_image_build_large_build_context_benchmark")
    @AnsibleMappedParams
    def image_build_large_build_context_benchmark(
            self,
            exec_props
    ):
        """
        Runs the image build large build context benchmark with the given runtime
        properties of exec_props:
          binary_path: path to the container engine binary (e.g., docker, podman)
          rootfull: whether to run the benchmark as root user
          additional_args: additional arguments to pass to the container engine binary
          exec_time_path: path to the exec_time.py script

        Args:
          exec_props: dict containing execution properties (binary_path, rootfull, additional_args, exec_time_path)
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
