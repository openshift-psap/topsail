import os
import pathlib
import logging

from projects.core.library import env, config, run, configure_logging, export
from projects.matrix_benchmarking.library import visualize

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
POD_VIRT_SECRET_PATH = pathlib.Path(os.environ.get("POD_VIRT_SECRET_PATH", "/env/POD_VIRT_SECRET_PATH/not_set"))

import ollama, prepare_mac_ai, remote_access, podman

def prepare_llm_load_test_args(base_work_dir, model_name):
    llm_load_test_kwargs = dict()

    model_size = config.project.get_config("test.model.size")

    llm_load_test_kwargs |= config.project.get_config(f"test.llm_load_test.args")
    llm_load_test_kwargs |= config.project.get_config(f"test.llm_load_test.dataset_sizes.{model_size}")

    if python_cmd := config.project.get_config("remote_host.python_cmd"):
        llm_load_test_kwargs["python_cmd"] = python_cmd

    if (port := llm_load_test_kwargs["port"]) and isinstance(port, str) and port.startswith("@"):
        llm_load_test_kwargs["port"] = config.project.get_config(port[1:])

    llm_load_test_kwargs |= dict(
        src_path = base_work_dir / "llm-load-test",
        model_id = model_name,
    )

    return llm_load_test_kwargs

def test():
    if config.project.get_config("test.platforms.native.enabled"):
        with env.NextArtifactDir("native_test"):
            test_ollama()

    if config.project.get_config("test.platforms.podman.enabled"):
        with env.NextArtifactDir("podman_test"):
            test_ollama(use_podman=True)

def test_ollama(use_podman=False):
    base_work_dir = remote_access.prepare()
    native_system = config.project.get_config("remote_host.system")
    model_name = config.project.get_config("test.model.name")

    podman_container_name = config.project.get_config("prepare.podman.container.name") \
        if use_podman else None

    ollama_path = ollama.get_binary_path(base_work_dir, native_system,
                                         podman=podman_container_name)

    llm_load_test_kwargs = prepare_llm_load_test_args(base_work_dir, model_name)

    if use_podman:
        podman.test()
        podman.start(base_work_dir, podman_container_name, llm_load_test_kwargs["port"])

    ollama.start(base_work_dir, ollama_path)
    ollama.run_model(base_work_dir, ollama_path, model_name)

    if config.project.get_config("test.llm_load_test.enabled"):
        run.run_toolbox(
            "llm_load_test", "run",
            **llm_load_test_kwargs
        )

    if config.project.get_config("prepare.ollama.unload_on_exit"):
        ollama.unload_model(base_work_dir, ollama_path, model_name)

    if config.project.get_config("prepare.ollama.stop_on_exit"):
        ollama.stop(base_work_dir, ollama_path)

    if use_podman and config.project.get_config("prepare.podman.stop_on_exit"):
        podman.stop(podman_container_name)


def matbench_run_one():
    pass
