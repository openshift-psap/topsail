import os
import pathlib
import logging
import yaml
import remote_access
import utils
import uuid
import sys

from projects.core.library import env, config, run
from projects.matrix_benchmarking.library import visualize, matbenchmark
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
        iterable_fields = config.project.get_config("test.matbenchmarking.iterable_test_fields")

        if config.project.get_config("test.matbenchmarking.enabled"):
            matbench_run(iterable_fields)
        else:
            test_all_benchmarks_and_platforms()
    except Exception as e:
        failed = True
        logging.error(f"Test failed: ({e})")
        raise
    finally:
        exc = None
        if config.project.get_config("matbench.enabled", print=False):
            exc = generate_visualization(env.ARTIFACT_DIR)
            if exc:
                logging.error(f"Test visualization failed :/ {exc}")

        logging.info(f"Test artifacts have been saved in {env.ARTIFACT_DIR}")

        if not failed and exc:
            raise exc

    return failed


def _separate_benchmark_values_by_platform(benchmark_values):
    platform_configs = {
        "podman": {},
        "docker": {}
    }
    common_values = {}
    for key, value in benchmark_values.items():
        if key.startswith("test.podman"):
            # Special handling for Windows and machine_provider not same as Darwin
            if key == "test.podman.machine_provider":
                if config.project.get_config("remote_host.system", print=False) == "linux":
                    continue
                is_windows = config.project.get_config("remote_host.system", print=False) == "windows"
                supported_hypervisors = ["wsl", "hyperv"] if is_windows else ["libkrun", "applehv"]
                value = [v for v in value if v in supported_hypervisors]
            platform_configs["podman"][key] = value
        elif key.startswith("test.docker"):
            platform_configs["docker"][key] = value
        elif key == "test.platform":
            _distribute_platform_values(platform_configs, value)
        else:
            common_values[key] = value

    for platform_config in platform_configs.values():
        if platform_config:
            platform_config.update(common_values)

    expe_to_run = {}
    for platform, platform_config in platform_configs.items():
        if platform_config:
            platform_config["test.platform"] = platform
            expe_to_run[f"container_bench_{platform}"] = platform_config

    return expe_to_run


def _distribute_platform_values(platform_configs, platform_values):
    for platform in platform_values:
        if platform.startswith("podman"):
            platform_configs["podman"].setdefault("test.platform", []).append(platform)
        elif platform.startswith("docker"):
            platform_configs["docker"].setdefault("test.platform", []).append(platform)
        else:
            logging.warning(f"Unknown platform type: {platform}")


def matbench_run(matrix_source_keys):
    with env.NextArtifactDir("matbenchmarking"):
        benchmark_values = {}

        for source_key in matrix_source_keys:
            source_values = config.project.get_config(source_key)
            logging.info(f"matbench_run: source_key={source_key}, source_values={source_values}")
            if isinstance(source_values, dict):
                for k, v in source_values.items():
                    if not isinstance(v, list):
                        continue

                    benchmark_values[f"{source_key}.{k}"] = v
            elif isinstance(source_values, list):
                benchmark_values[source_key] = source_values

        expe_to_run = _separate_benchmark_values_by_platform(benchmark_values)

        logging.info(f"matbench_run: expe_to_run={expe_to_run}")

        old_version = config.project.get_config("prepare.podman.repo.version", print=False)
        old_is_repo_enabled = config.project.get_config("prepare.podman.repo.enabled", print=False)
        old_is_enabled_custom = config.project.get_config("prepare.podman.custom_binary.enabled", print=False)
        base_work_dir = remote_access.prepare()
        versions = expe_to_run.get("container_bench_podman", {}).get("test.podman.repo_version", [])
        for v in versions:
            logging.info(f"matbench_run: setting test.podman.repo_version={v}")
            if v == "custom":
                config.project.set_config("prepare.podman.custom_binary.enabled", True)
                if config.project.get_config("prepare.podman.custom_binary.enabled", print=False):
                    utils.prepare_custom_podman_binary(base_work_dir)
            else:
                config.project.set_config("prepare.podman.repo.enabled", True)
                config.project.set_config("prepare.podman.repo.version", v)
                if config.project.get_config("prepare.podman.repo.enabled"):
                    utils.prepare_podman_from_gh_binary(base_work_dir)

        config.project.set_config("prepare.podman.repo.version", old_version)
        config.project.set_config("prepare.podman.repo.enabled", old_is_repo_enabled)
        config.project.set_config("prepare.podman.custom_binary.enabled", old_is_enabled_custom)

        json_benchmark_file = matbenchmark.prepare_benchmark_file(
            path_tpl="test",
            script_tpl=f"{sys.argv[0]} matbench_run",
            stop_on_error=config.project.get_config("test.matbenchmarking.stop_on_error"),
            common_settings=dict(),
            test_files={},
            expe_to_run=expe_to_run,
        )

        logging.info(f"Benchmark configuration to run: \n{yaml.dump(json_benchmark_file, sort_keys=False)}")

        benchmark_file, yaml_content = matbenchmark.save_benchmark_file(json_benchmark_file)

        args = matbenchmark.set_benchmark_args(benchmark_file)

        failed = matbenchmark.run_benchmark(args)
        if failed:
            msg = "_run_test_matbenchmarking: matbench benchmark failed :/"
            logging.error(msg)
            raise RuntimeError(msg)

        if config.project.get_config("cleanup.files.podman"):
            logging.info("Cleaning up Podman files")
            for v in versions:
                if v == "custom":
                    continue
                config.project.set_config("prepare.podman.repo.version", v)
                utils.cleanup_podman_files(base_work_dir)
            config.project.set_config("prepare.podman.repo.version", old_version)


def matbench_run_one():
    with env.TempArtifactDir(RUN_DIR):
        with open(env.ARTIFACT_DIR / "settings.yaml") as f:
            settings = yaml.safe_load(f)
        logging.info(f"matbench_run_one: settings={settings}")

        with open(env.ARTIFACT_DIR / "skip", "w") as f:
            print("Results are in a subdirectory, not here.", file=f)

        map_key = config.project.get_config("test.matbenchmarking.map_iterable_test_fields", print=False)
        logging.info(f"matbench_run_one: map_key={map_key}")
        for k, v in settings.items():
            logging.info(f"matbench_run_one: setting {k}={v}")
            if k not in map_key:
                raise ValueError(f"matbench_run_one: No mapping for {k} in test.matbenchmarking.map")
            if k == "test.podman.repo_version":
                if v == "custom":
                    config.project.set_config("prepare.podman.custom_binary.enabled", True)
                else:
                    config.project.set_config("prepare.podman.repo.enabled", True)
            if type(map_key[k]) is list:
                for k in map_key[k]:
                    logging.info(f"matbench_run_one: setting {k}={v}")
                    config.project.set_config(k, v)
            else:
                config.project.set_config(map_key[k], v)

        config.project.set_config("test.matbenchmarking.enabled", False)

        platform_str = config.project.get_config("test.platform")

        if platform_str in (config.project.get_config("test.platforms_to_skip", print=False) or []):
            logging.info(f"Skipping {platform_str} test as per test.platforms_to_skip.")
            return

        all_benchmarks_str = config.project.get_config("test.benchmark")
        if isinstance(all_benchmarks_str, str):
            all_benchmarks_str = [all_benchmarks_str]
        benchmarks = [utils.parse_benchmark(b) for b in all_benchmarks_str]
        run_benchmarks_for_specific_platform(platform_str, benchmarks)


def run_benchmarks_for_specific_platform(platform_str, benchmarks):
    platform = utils.parse_platform(platform_str)
    platform.prepare_platform()
    try:
        for benchmark in benchmarks:
            if platform.container_engine not in benchmark.supported_container_engines:
                continue  # skip unsupported benchmarks
            config.project.set_config("test.platform", platform_str)  # for the post-processing
            config.project.set_config("test.benchmark", benchmark.name)  # for the post-processing
            with env.NextArtifactDir(f"{platform_str}_{benchmark.name}_run_dir".replace("/", "_")):
                with open(env.ARTIFACT_DIR / "settings.yaml", "w") as f:
                    yaml.dump(dict(
                        platform=platform_str,
                        container_engine=platform.container_engine,
                        benchmark=benchmark.name,
                        benchmark_runs=benchmark.runs,
                    ), f)
                logging.info(f"Run benchmark: {benchmark.name} on {platform_str}")
                run_benchmark(platform, benchmark)
    finally:
        platform.cleanup_platform()


def test_all_benchmarks_and_platforms():
    all_benchmarks_str = config.project.get_config("test.benchmark")
    if isinstance(all_benchmarks_str, str):
        all_benchmarks_str = [all_benchmarks_str]
    benchmarks = [utils.parse_benchmark(b) for b in all_benchmarks_str]

    all_platforms_str = config.project.get_config("test.platform")
    if isinstance(all_platforms_str, str):
        all_platforms_str = [all_platforms_str]

    for platform_str in all_platforms_str:
        if platform_str in (config.project.get_config("test.platforms_to_skip", print=False) or []):
            continue
        run_benchmarks_for_specific_platform(platform_str, benchmarks)


def capture_metrics(platform):
    if not config.project.get_config("test.capture_metrics.enabled", print=False):
        logging.info("capture_metrics: Metrics capture not enabled.")
        return
    c = ContainerEngine(platform.container_engine)
    run.run_toolbox(
        "container_bench", "capture_container_engine_info",
        binary_path=c.engine_binary,
        rootfull=c.is_rootful(),
        additional_args=c.additional_args(),
    )

    run.run_toolbox("container_bench", "capture_system_state")


def prepare_benchmark_args(platform, benchmark, base_work_dir):
    c = ContainerEngine(platform.container_engine)
    benchmark_kwargs = dict(
        binary_path=c.engine_binary,
        rootfull=c.is_rootful(),
        additional_args=c.additional_args(),
        exec_time_path=utils.get_benchmark_script_path(base_work_dir),
        artifact_dir_suffix="_run_metrics"
    )

    return {k: config.project.resolve_reference(v) for k, v in benchmark_kwargs.items()}


def prepare_matbench_test_files():
    settings_file = env.ARTIFACT_DIR / "settings.yaml"
    if settings_file.exists():
        with open(settings_file) as f:
            settings_base = yaml.safe_load(f)
    else:
        settings_base = {}

    # ensure that there's no skip file here
    (env.ARTIFACT_DIR / "skip").unlink(missing_ok=True)

    settings = settings_base | dict(
        test_mac_ai=True,
    )

    with open(settings_file, "w") as f:
        yaml.dump(settings, f, indent=4)

    with open(env.ARTIFACT_DIR / "config.yaml", "w") as f:
        yaml.dump(config.project.config, f, indent=4)

    with open(env.ARTIFACT_DIR / ".uuid", "w") as f:
        print(str(uuid.uuid4()), file=f)


def run_benchmark(platform, benchmark):
    base_work_dir = remote_access.prepare()

    capture_metrics(platform)
    prepare_matbench_test_files()
    exit_code = 1
    try:
        for _ in range(benchmark.runs):
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
        if exc:
            logging.error(f"Test visualization failed :/ {exc}")
        logging.info(f"Test visualization has been generated into {env.ARTIFACT_DIR}/reports_index.html")

    return exc
