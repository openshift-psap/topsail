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
            base_work_dir,
            runtime
    ):
        """
        Runs the helloworld benchmark with the given runtime
        Args:
          base_work_dir: the base directory where to store things
          runtime: the runtime to use for the benchmark (e.g., docker, podman)
        """
        return RunAnsibleRole(locals())

    @AnsibleRole("container_bench_capture_power_usage")
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

    @AnsibleRole("container_bench_capture_cpu_ram_usage")
    @AnsibleMappedParams
    def remote_capture_cpu_ram_usage(
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
    def remote_capture_system_state(
            self,
    ):
        """
        Captures the state of the remote Mac system

        Args:
        """

        return RunAnsibleRole(locals())
