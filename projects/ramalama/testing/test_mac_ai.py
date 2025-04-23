import os, sys
import pathlib
import logging
import yaml
import uuid

from projects.core.library import env, config, run, configure_logging, export
from projects.matrix_benchmarking.library import visualize, matbenchmark

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
TOPSAIL_DIR = pathlib.Path(config.__file__).parents[3]
CRC_MAC_AI_SECRET_PATH = pathlib.Path(os.environ.get("CRC_MAC_AI_SECRET_PATH", "/env/CRC_MAC_AI_SECRET_PATH/not_set"))

# not using `os.getcwd()` anymore because of
# https://stackoverflow.com/questions/1542803/is-there-a-version-of-os-getcwd-that-doesnt-dereference-symlinks
RUN_DIR = pathlib.Path(os.getenv('PWD')) # for run_one_matbench
os.chdir(TOPSAIL_DIR)

import prepare_mac_ai, remote_access, podman, podman_machine, brew, utils

def prepare_llm_load_test_args(base_work_dir, model_id):
    llm_load_test_kwargs = dict()

    model_size = config.project.get_config("test.model.size")

    llm_load_test_kwargs |= config.project.get_config(f"test.llm_load_test.args")
    llm_load_test_kwargs |= config.project.get_config(f"test.llm_load_test.dataset_sizes.{model_size}")

    if python_bin := config.project.get_config("remote_host.python_bin"):
        llm_load_test_kwargs["python_cmd"] = python_bin

    llm_load_test_kwargs |= dict(
        src_path = base_work_dir / "llm-load-test",
        model_id = model_id,
    )

    return {k:config.project.resolve_reference(v) for k, v in llm_load_test_kwargs.items()}


def prepare_matbench_test_files():
    model_name = config.project.get_config("test.model.name")

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


def safety_checks():
    do_matbenchmarking = config.project.get_config("test.matbenchmarking.enabled")
    all_platforms = config.project.get_config("test.platform")

    multi_test = do_matbenchmarking or not isinstance(all_platforms, str)
    if not multi_test:
        return # safe

    keep_running = not config.project.get_config("test.inference_server.unload_on_exit")

    if not keep_running:
        return # safe

    # unsafe
    msg = "test.inference_server.unload_on_exit cannot be enabled when running multiple tests"
    logging.fatal(msg)
    raise ValueError(msg)


def test():
    safety_checks()

    if config.project.get_config("prepare.podman.machine.enabled"):
        base_work_dir = remote_access.prepare()
        podman_machine.configure_and_start(base_work_dir, force_restart=False)

    failed = False
    try:
        do_matbenchmarking = config.project.get_config("test.matbenchmarking.enabled")

        if config.project.get_config("test.matbenchmarking.enabled"):
            matbench_run(config.project.get_config("test.matbenchmarking.fields"))
        else:
            platform_str = config.project.get_config("test.platform")
            test_inference(utils.parse_platform(platform_str))
    except Exception as e:
        failed = True
        logging.error(f"Test failed :/ ({e})")
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


def capture_metrics(platform, stop=False):
    if not config.project.get_config("test.capture_metrics.enabled"):
        logging.info("capture_metrics: Metrics capture not enabled.")

        return

    if config.project.get_config("test.capture_metrics.gpu.enabled"):
        sampler = config.project.get_config("test.capture_metrics.gpu.sampler")

        artifact_dir_suffix = f"_{sampler}"
        if stop:
            artifact_dir_suffix += "_stop"
        run.run_toolbox(
            "mac_ai", "remote_capture_power_usage",
            samplers=sampler,
            sample_rate=config.project.get_config("test.capture_metrics.gpu.rate"),
            stop=stop,
            mute_stdout=stop,
            artifact_dir_suffix=artifact_dir_suffix,
        )


    if (config.project.get_config("test.capture_metrics.virtgpu.enabled")
        and platform.needs_podman_machine):

        run.run_toolbox(
            "mac_ai", "remote_capture_virtgpu_memory",
            podman_machine_ssh_cmd=podman_machine.get_ssh_command_prefix(),
            stop=stop,
            mute_stdout=stop,
            artifact_dir_suffix="_stop" if stop else None,
        )

    run.run_toolbox(
        "mac_ai", "remote_capture_cpu_ram_usage",
        stop=stop,
        mute_stdout=stop,
        artifact_dir_suffix="_stop" if stop else None,
    )

    if not stop:
        run.run_toolbox(
            "mac_ai", "remote_capture_system_state",
        )


def test_inference(platform):
    base_work_dir = remote_access.prepare()

    model_name = config.project.get_config("test.model.name")

    inference_server_path = platform.prepare_inference_server_mod.get_binary_path(
        base_work_dir, platform,
    )

    platform.inference_server_mod.unload_model(base_work_dir, platform, inference_server_path, model_name)

    brew.capture_dependencies_version(base_work_dir)

    if platform.needs_podman_machine:
        if not podman_machine.is_running(base_work_dir):
            podman_machine.start(base_work_dir)

        if platform.needs_podman:
            inference_server_port = config.project.get_config("test.inference_server.port")
            podman.start(base_work_dir, inference_server_port)

    elif podman_machine.is_running(base_work_dir):
        podman.stop(base_work_dir)
        podman_machine.stop(base_work_dir)

    inference_server_binary = platform.prepare_inference_server_mod.get_binary_path(base_work_dir, platform)

    if not platform.inference_server_mod.has_model(base_work_dir, inference_server_binary, model_name):
        platform.inference_server_mod.pull_model(base_work_dir, inference_server_binary, model_name)

    llm_load_test_enabled = config.project.get_config("test.llm_load_test.enabled")
    server_benchmark_enabled = config.project.get_config("test.inference_server.benchmark.enabled")

    if not (llm_load_test_enabled or server_benchmark_enabled):
        return

    capture_metrics(platform)
    prepare_matbench_test_files()
    exit_code = 1

    try:
        if server_benchmark_enabled:
            platform.inference_server_mod.run_benchmark(
                base_work_dir,
                platform,
                inference_server_path,
                model_name,
            )

        model_id = platform.inference_server_mod.run_model(
            base_work_dir, platform, inference_server_path, model_name
        )

        if llm_load_test_enabled:
            run.run_toolbox(
                "llm_load_test", "run",
                **prepare_llm_load_test_args(base_work_dir, model_id)
            )

        exit_code = 0
    finally:
        exc = None

        if config.project.get_config("test.inference_server.unload_on_exit"):
            exc = run.run_and_catch(exc, platform.inference_server_mod.unload_model,
                                    base_work_dir, platform, inference_server_path, model_name)


        if platform.needs_podman and config.project.get_config("prepare.podman.stop_on_exit"):
            exc = run.run_and_catch(exc, podman.stop, base_work_dir)

        if not config.project.get_config("remote_host.run_locally"):
            # retrieve all the files that have been saved remotely
            exc = run.run_and_catch(exc, run.run_toolbox, "remote", "retrieve",
                                    path=env.ARTIFACT_DIR, dest=env.ARTIFACT_DIR,
                                    mute_stdout=True, mute_stderr=True)

        with open(env.ARTIFACT_DIR / "exit_code", "w") as f:
            print(exit_code, file=f)

        exc = run.run_and_catch(exc, capture_metrics, platform, stop=True)

        if exc:
            logging.exception(f"Test tear-down crashed ({exc})")


def matbench_run(matrix_source_keys):
    with env.NextArtifactDir("matbenchmarking"):
        benchmark_values = {}

        for source_key in matrix_source_keys:
            source_values = config.project.get_config(source_key)
            if isinstance(source_values, dict):
                for k, v in source_values.items():
                    if not isinstance(v, list):
                        continue

                    benchmark_values[f"{source_key}.{k}"] = v
            elif isinstance(source_values, list):
                benchmark_values[source_key] = source_values

        expe_to_run = dict(mac_ai=benchmark_values)

        if not benchmark_values:
            logging.info("No benchmark values to pass to MatrixBenchmarking. Skipping it.")
            test_inference(utils.parse_platform(config.project.get_config("test.platform")))

            return

        first_key = list(benchmark_values)[0]
        first_key_name = first_key.rpartition(".")[-1]
        path_tpl = f"test"

        json_benchmark_file = matbenchmark.prepare_benchmark_file(
            path_tpl=path_tpl,
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
            msg = f"_run_test_matbenchmarking: matbench benchmark failed :/"
            logging.error(msg)
            raise RuntimeError(msg)


def matbench_run_one():
    with env.TempArtifactDir(RUN_DIR):
        with open(env.ARTIFACT_DIR / "settings.yaml") as f:
            settings = yaml.safe_load(f)

        with open(env.ARTIFACT_DIR / "skip", "w") as f:
            print("Results are in a subdirectory, not here.", file=f)

        for k, v in settings.items():
            config.project.set_config(k, v)

        config.project.set_config("test.matbenchmarking.enabled", False)

        platform_str = config.project.get_config("test.platform")

        if platform_str in (config.project.get_config("test.platforms_to_skip", print=False) or []):
            logging.info(f"Skipping {platform_str} test as per test.platforms_to_skip.")
            return

        test_inference(utils.parse_platform(platform_str))


def generate_visualization(test_artifact_dir):
    exc = None

    with env.NextArtifactDir("plots"):
        exc = run.run_and_catch(exc, visualize.generate_from_dir, test_artifact_dir)

        logging.info(f"Test visualization has been generated into {env.ARTIFACT_DIR}/reports_index.html")

    return exc
