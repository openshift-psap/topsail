import os
import pathlib
import logging
import yaml
import remote_access
import utils

from projects.core.library import env, config, run
from projects.matrix_benchmarking.library import visualize

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
TOPSAIL_DIR = pathlib.Path(config.__file__).parents[3]

# not using `os.getcwd()` anymore because of
# https://stackoverflow.com/questions/1542803/is-there-a-version-of-os-getcwd-that-doesnt-dereference-symlinks
RUN_DIR = pathlib.Path(os.getenv('PWD'))  # for run_one_matbench
os.chdir(TOPSAIL_DIR)


def safety_checks():
    do_matbenchmarking = config.project.get_config("test.matbenchmarking.enabled")
    all_platforms = config.project.get_config("test.platform")

    multi_test = do_matbenchmarking or not isinstance(all_platforms, str)
    if not multi_test:
        return  # safe

    keep_running = not config.project.get_config("test.inference_server.unload_on_exit")

    if not keep_running:
        return  # safe

    # unsafe
    msg = "test.inference_server.unload_on_exit cannot be enabled when running multiple tests"
    logging.fatal(msg)
    raise ValueError(msg)


def test():
    safety_checks()

    failed = False
    try:
        # TODO: run multiple time to avoid outlaying runs
        test_all_benchmark()
    except Exception as e:
        failed = True
        logging.error(f"Test failed: ({e})")
        raise
    finally:
        exc = None
        if config.project.get_config("matbench.enabled"):
            exc = generate_visualization(env.ARTIFACT_DIR)
            if exc:
                logging.error(f"Test visualization failed :/ {exc}")

        logging.info(f"Test artifacts have been saved in {env.ARTIFACT_DIR}")

        if not failed and exc:
            raise exc


def test_all_benchmark():
    all_benchmarks_str = config.project.get_config("test.platform")
    if isinstance(all_benchmarks_str, str):
        run_benchmark(utils.parse_benchmark(all_benchmarks_str))
        return

    for benchmark_str in all_benchmarks_str:
        if benchmark_str in config.project.get_config("test.platforms_to_skip", print=False):
            continue

        config.project.set_config("test.platform", benchmark_str)  # for the post-processing

        logging.info(f"Run benchmark: {benchmark_str}")
        with env.NextArtifactDir(f"{benchmark_str}_test".replace("/", "_")):
            with open(env.ARTIFACT_DIR / "settings.platform.yaml", "w") as f:
                yaml.dump(dict(platform=benchmark_str, benchmark=benchmark_str), f)
            run_benchmark(utils.parse_benchmark(benchmark_str))


def capture_metrics(stop=False):
    if not config.project.get_config("test.capture_metrics.enabled"):
        logging.info("capture_metrics: Metrics capture not enabled.")
        return

    if config.project.get_config("test.capture_metrics.power.enabled"):
        sampler = config.project.get_config("test.capture_metrics.power.sampler")

        artifact_dir_suffix = f"_{sampler}"
        if stop:
            artifact_dir_suffix += "_stop"
        run.run_toolbox(
            "container_bench", "capture_power_usage",
            samplers=sampler,
            sample_rate=config.project.get_config("test.capture_metrics.power.rate"),
            stop=stop,
            mute_stdout=stop,
            artifact_dir_suffix=artifact_dir_suffix,
        )

    run.run_toolbox(
        "container_bench", "capture_cpu_ram_usage",
        stop=stop,
        mute_stdout=stop,
        artifact_dir_suffix="_stop" if stop else None,
    )

    if not stop:
        run.run_toolbox(
            "container_bench", "capture_system_state",
        )


def prepare_benchmark_args(benchamrk, base_work_dir):
    benchmark_kwargs = dict(
        src_path=base_work_dir / benchamrk.benchmark,
        runtime=benchamrk.container_engine,
    )

    return {k: config.project.resolve_reference(v) for k, v in benchmark_kwargs.items()}


def run_benchmark(benchmark):
    base_work_dir = remote_access.prepare()

    capture_metrics()
    exit_code = 1
    try:
        run.run_toolbox(
                "container_bench",
                benchmark.benchmark,
                **prepare_benchmark_args(benchmark, base_work_dir)
        )
        exit_code = 0
    finally:
        exc = None
        if not config.project.get_config("remote_host.run_locally"):
            # retrieve all the files that have been saved remotely
            exc = run.run_and_catch(exc, run.run_toolbox, "remote", "retrieve",
                                    path=env.ARTIFACT_DIR, dest=env.ARTIFACT_DIR,
                                    mute_stdout=True, mute_stderr=True)

        with open(env.ARTIFACT_DIR / "exit_code", "w") as f:
            print(exit_code, file=f)

        exc = run.run_and_catch(exc, capture_metrics, stop=True)

        if exc:
            logging.exception(f"Test tear-down crashed ({exc})")


def generate_visualization(test_artifact_dir):
    exc = None

    with env.NextArtifactDir("plots"):
        exc = run.run_and_catch(exc, visualize.generate_from_dir, test_artifact_dir)

        logging.info(f"Test visualization has been generated into {env.ARTIFACT_DIR}/reports_index.html")

    return exc
