import os
import pathlib
import logging
import yaml
import remote_access
import utils

from projects.core.library import env, config, run
from projects.matrix_benchmarking.library import visualize
from container_engine import ContainerEngine

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
TOPSAIL_DIR = pathlib.Path(config.__file__).parents[3]

# not using `os.getcwd()` anymore because of
# https://stackoverflow.com/questions/1542803/is-there-a-version-of-os-getcwd-that-doesnt-dereference-symlinks
_pwd = os.getenv('PWD')
RUN_DIR = pathlib.Path(_pwd if _pwd else os.getcwd())  # for run_one_matbench
os.chdir(TOPSAIL_DIR)


def safety_checks():
    do_matbenchmarking = config.project.get_config("test.matbenchmarking.enabled")
    all_platforms = config.project.get_config("test.platform")

    multi_test = do_matbenchmarking or not isinstance(all_platforms, str)
    if not multi_test:
        return  # safe
    # TODO: check
    return


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
        if config.project.get_config("matbench.enabled", print=False):
            # TODO implement visualization for matbench and matchbench
            exc = generate_visualization(env.ARTIFACT_DIR)
            if exc:
                logging.error(f"Test visualization failed :/ {exc}")

        logging.info(f"Test artifacts have been saved in {env.ARTIFACT_DIR}")

        if not failed and exc:
            raise exc

    return failed


def test_all_benchmark():
    all_benchmarks_str = config.project.get_config("test.benchmark")
    if isinstance(all_benchmarks_str, str):
        all_benchmarks_str = [all_benchmarks_str]
    benchmarks = [utils.parse_benchmark(b) for b in all_benchmarks_str]

    all_platforms_str = config.project.get_config("test.platform")
    if isinstance(all_platforms_str, str):
        all_platforms_str = [all_platforms_str]

    for platform_str in all_platforms_str:
        if platform_str in config.project.get_config("test.platforms_to_skip", print=False):
            continue
        platform = utils.parse_platform(platform_str)
        for benchmark in benchmarks:
            if platform.container_engine not in benchmark.supported_container_engines:
                continue  # skip unsupported benchmarks
            config.project.set_config("test.platform", platform_str)  # for the post-processing
            config.project.set_config("test.benchmark", benchmark.name)  # for the post-processing
            with env.NextArtifactDir(f"{platform_str}_{benchmark.name}_run_dir".replace("/", "_")):
                with open(env.ARTIFACT_DIR / "settings.platform.yaml", "w") as f:
                    yaml.dump(dict(platform=platform_str), f)
                with open(env.ARTIFACT_DIR / "settings.benchmarks.yaml", "w") as f:
                    yaml.dump(dict(benchmark=benchmarks), f)
                logging.info(f"Run benchmark: {benchmark.name} on {platform_str}")
                run_benchmark(platform, benchmark)


def capture_metrics(platform):
    if not config.project.get_config("test.capture_metrics.enabled", print=False):
        logging.info("capture_metrics: Metrics capture not enabled.")
        return
    c = ContainerEngine(platform.container_engine)
    run.run_toolbox(
        "container_bench", "capture_container_engine_info",
        runtime=c.engine_binary,
    )
    if platform.platform == "darwin":
        run.run_toolbox("container_bench", "capture_system_state")


def prepare_benchmark_args(platform, benchmark, base_work_dir):
    c = ContainerEngine(platform.container_engine)
    benchmark_kwargs = dict(
        runtime=c.engine_binary,
        exec_time_path=utils.get_benchmark_script_path(base_work_dir),
        artifact_dir_suffix="_run_metrics"
    )

    return {k: config.project.resolve_reference(v) for k, v in benchmark_kwargs.items()}


def run_benchmark(platform, benchmark):
    base_work_dir = remote_access.prepare()

    capture_metrics(platform)
    exit_code = 1
    try:
        run.run_toolbox(
                "container_bench",
                benchmark.name,
                **prepare_benchmark_args(platform, benchmark, base_work_dir)
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

        if exc:
            logging.exception(f"Test tear-down crashed ({exc})")


def generate_visualization(test_artifact_dir):
    exc = None

    with env.NextArtifactDir("plots"):
        exc = run.run_and_catch(exc, visualize.generate_from_dir, test_artifact_dir)

        logging.info(f"Test visualization has been generated into {env.ARTIFACT_DIR}/reports_index.html")

    return exc
