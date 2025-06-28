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
            working_dir,
            runtime,
    ):
        """
        Runs the helloworld benchmark with the given runtime
        Args:
          exec_time_path: path to the exec_time.py script
          working_dir: the working directory for the benchmark
          runtime: the runtime to use for the benchmark (e.g., docker, podman)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_capture_power_usage")
    @AnsibleMappedParams
    def capture_power_usage(
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

    @AnsibleRole("container_bench_capture_cpu_ram_usage")
    @AnsibleMappedParams
    def capture_cpu_ram_usage(
            self,
            stop=False,
    ):
        """
        Captures the CPU and RAM usage on Unix-like systems

        Args:
          stop: if true, only stop the capture
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

    @AnsibleRole("container_bench_copy_file_to_remote")
    @AnsibleMappedParams
    def copy_file_to_remote(
            self,
            source,
            dest,
    ):
        """
        Copies a file from the local machine to the remote machine
        Args:
          source: the source file to copy
          dest: the destination path on the remote machine
        """

        return RunAnsibleRole(locals())
