import os
import pathlib
import logging

from projects.core.library import env, config, run, configure_logging, export
from projects.matrix_benchmarking.library import visualize

import ollama, llama_cpp, utils, remote_access, podman_machine, brew

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
CRC_MAC_AI_SECRET_PATH = pathlib.Path(os.environ.get("CRC_MAC_AI_SECRET_PATH", "/env/CRC_MAC_AI_SECRET_PATH/not_set"))

INFERENCE_SERVERS = dict(
    ollama=ollama,
    llama_cpp=llama_cpp,
)

def prepare():
    base_work_dir = remote_access.prepare()

    podman_machine.configure_and_start(base_work_dir, force_restart=True)

    prepare_llm_load_test(base_work_dir)
    brew.install_dependencies(base_work_dir)

    inference_server_name = config.project.get_config("test.inference_server.name")
    inference_server_mod = INFERENCE_SERVERS.get(inference_server_name)
    if not inference_server_mod:
        msg = f"Invalid inference server ({inference_server_name}). Expected one of {', '.join(INFERENCE_SERVERS)}"
        logging.fatal(msg)
        raise ValueError(msg)

    native_system = config.project.get_config("remote_host.system")
    inference_server_binaries = {}

    for system in config.project.get_config("prepare.systems"):
        inference_server_binaries[system] = inference_server_mod.prepare_binary(base_work_dir, system)

    inference_server_native_binary = inference_server_binaries[native_system]

    model = config.project.get_config("test.model.name")

    inference_server_mod.start(base_work_dir, inference_server_native_binary)
    try:
        inference_server_mod.pull_model(base_work_dir, inference_server_native_binary, model)
    finally:
        inference_server_mod.stop(base_work_dir, inference_server_native_binary)


    if config.project.get_config("prepare.podman.machine.enabled"):
        podman_machine.configure_and_start(base_work_dir, force_restart=False)

    return 0


def prepare_llm_load_test(base_work_dir):
    # running this locally to know llm-load-test is configured in TOPSAIL's repo
    submodule_status = run.run("git submodule status | grep llm-load-test", capture_stdout=True).stdout
    submodule_commit = submodule_status.split()[0].replace("+", "")
    submodule_path = submodule_status.split()[1]
    repo_url= run.run(f"git config --file=.gitmodules submodule.'{submodule_path}'.url", capture_stdout=True).stdout.strip()

    dest = base_work_dir / "llm-load-test"

    if dest.exists():
        logging.info(f"{dest} already exists, not cloning it.")
        return

    run.run_toolbox(
        "remote", "clone",
        repo_url=repo_url, dest=dest, version=submodule_commit,
    )

    python_bin = config.project.get_config("remote_host.python_bin", "python3")

    remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{python_bin} -m pip install -r {dest}/requirements.txt",
    )
