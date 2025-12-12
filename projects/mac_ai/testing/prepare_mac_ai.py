import os, sys
import pathlib
import logging
import subprocess

from projects.core.library import env, config, run, configure_logging, export
from projects.matrix_benchmarking.library import visualize

import utils, podman_machine, brew, podman, prepare_virglrenderer, prepare_release
import prepare_llama_cpp, llama_cpp, ollama, ramalama, lightspeed
from projects.remote.lib import remote_access

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
CRC_MAC_AI_SECRET_PATH = pathlib.Path(os.environ.get("CRC_MAC_AI_SECRET_PATH", "/env/CRC_MAC_AI_SECRET_PATH/not_set"))

PREPARE_INFERENCE_SERVERS = dict(
    llama_cpp=prepare_llama_cpp,
    ollama=ollama,
    ramalama=ramalama,
    lightspeed=lightspeed,
)

INFERENCE_SERVERS = dict(
    llama_cpp=llama_cpp,
    ollama=ollama,
    ramalama=ramalama,
    lightspeed=lightspeed,
)


REMOTING_FRONTEND_PLATFORM = "podman/llama_cpp/remoting"
REMOTING_BACKEND_PLATFORM = {
    "darwin": "macos/llama_cpp/remoting",
    "linux": "linux/llama_cpp/remoting",
}
RAMALAMA_REMOTING_PLATFORM = "podman/ramalama/remoting"

def cleanup():
    base_work_dir = remote_access.prepare()

    if config.project.get_config("cleanup.images.llama_cpp"):
        if config.project.get_config("prepare.podman.machine.enabled"):
            is_running = podman_machine.is_running(base_work_dir)
            if is_running is None:
                logging.warning("Podman machine doesn't exist.")
            elif not is_running:
                try:
                    podman_machine.start(base_work_dir, use_remoting=False)
                    is_running = True
                except subprocess.CalledProcessError:
                    logging.warning("Could not start podman machine, cannot cleanup the llama_cpp images ...")
                    is_running = None
        else:
            is_running = True

        if is_running:
            prepare_llama_cpp.cleanup_image(base_work_dir)

    # ***

    if config.project.get_config("cleanup.files.ollama"):
        ollama.cleanup_files(base_work_dir)

    if config.project.get_config("cleanup.models.ollama"):
        ollama.cleanup_models(base_work_dir)

    if config.project.get_config("cleanup.models.gguf"):
        cleanup_gguf_models(base_work_dir)

    if config.project.get_config("cleanup.models.ramalama"):
        ramalama.cleanup_models(base_work_dir)

    # ***

    if config.project.get_config("cleanup.files.llm-load-test"):
        cleanup_llm_load_test(base_work_dir)

    if config.project.get_config("cleanup.files.llama_cpp"):
        prepare_llama_cpp.cleanup_files(base_work_dir)

    if config.project.get_config("cleanup.files.ramalama"):
        ramalama.cleanup_files(base_work_dir)

    if config.project.get_config("cleanup.files.lightspeed"):
        lightspeed.cleanup_files(base_work_dir)

    if config.project.get_config("cleanup.images.lightspeed"):
        lightspeed.cleanup_images(base_work_dir)

    # ***

    if config.project.get_config("cleanup.podman_machine.delete"):
        is_running = podman_machine.is_running(base_work_dir)
        if is_running:
            podman_machine.stop(base_work_dir)
            is_running = podman_machine.is_running(base_work_dir)

        if is_running is not None:
            podman_machine.rm(base_work_dir)

        if config.project.get_config("cleanup.podman_machine.reset"):
            try:
                podman_machine.reset(base_work_dir)
            except subprocess.CalledProcessError as e:
                if e.returncode != 127:
                    raise
                logging.info("Cannot reset podman machine, podman binary already cleaned up.")

    if config.project.get_config("cleanup.files.podman"):
        podman.cleanup(base_work_dir)

    if config.project.get_config("cleanup.files.virglrenderer"):
        prepare_virglrenderer.cleanup(base_work_dir)


    return 0


def prepare():
    base_work_dir = remote_access.prepare()

    if not config.project.get_config("prepare.prepare_only_inference_server"):
        run.run_toolbox("mac_ai", "remote_capture_system_state")

        if config.project.get_config("prepare.podman.repo.enabled"):
            podman.prepare_from_gh_binary(base_work_dir)
            podman.prepare_gv_from_gh_binary(base_work_dir)

        brew.install_dependencies(base_work_dir)

        prepare_llm_load_test(base_work_dir)

        prepare_virglrenderer.prepare(base_work_dir)

        if config.project.get_config("prepare.podman.machine.enabled"):
            podman_machine.configure_and_start(base_work_dir, force_restart=True)

    platforms_to_build_str = config.project.get_config("prepare.platforms.to_build")
    if not platforms_to_build_str:
        platforms_to_build_str = config.project.get_config("test.platform")

    if not isinstance(platforms_to_build_str, list):
        platforms_to_build_str = [platforms_to_build_str]

    system = config.project.get_config("remote_host.system")
    if REMOTING_FRONTEND_PLATFORM in platforms_to_build_str and system == "darwin":
        backend_platform = REMOTING_BACKEND_PLATFORM[system]
        if backend_platform not in platforms_to_build_str:
            platforms_to_build_str.append(backend_platform)

    puller_platforms = []
    platforms_to_build = [
        utils.parse_platform(platform_str)
        for platform_str in platforms_to_build_str
    ]

    for platform in platforms_to_build.copy(): # use a copy as we may discover new platforms to build in the loop
        model_puller_str = config.project.get_config(f"prepare.platforms.model_pullers.{platform.inference_server_name}")
        puller_platform = utils.parse_platform(model_puller_str)
        puller_platforms.append(puller_platform)

        if model_puller_str not in platforms_to_build_str:
            platforms_to_build.append(puller_platform)

    platform_binaries = {}
    system = config.project.get_config("remote_host.system")
    for platform in platforms_to_build:
        ignore = False
        ignore |= (platform.system == "macos" and system == "linux")
        ignore |= (platform.system == "linux" and system == "darwin")

        if ignore:
            logging.warning(f"Ignoring platform {platform} on {system}.")
            continue

        inference_server_config = config.project.get_config(f"prepare.{platform.inference_server_name}", None, print=False)
        if not inference_server_config:
            raise ValueError(f"Cannot prepare the {platform.inference_server_name} inference server: no configuration available :/")

        def prepare_binary():
            # keep only the last binary per platform, on purpose (we
            # only need to save a native platform binary in this
            # prepare step)
            platform_binaries[platform.name] = platform.prepare_inference_server_mod.prepare_binary(base_work_dir, platform)

        run.run_iterable_fields(
            inference_server_config.get("iterable_build_fields"),
            prepare_binary
        )

    # --- #

    models = config.project.get_config("test.model.name")

    platforms_pulled = set()
    for puller_platform in puller_platforms:
        if puller_platform.name in platforms_pulled: continue

        inference_server_binary = platform_binaries[puller_platform.name]
        try:
            puller_platform.inference_server_mod.start_server(base_work_dir, puller_platform, inference_server_binary)
            for model in models if isinstance(models, list) else [models]:
                config.project.set_config("test.model.name", model)

                if puller_platform.inference_server_mod.has_model(base_work_dir, puller_platform, inference_server_binary, model):
                    continue

                puller_platform.inference_server_mod.pull_model(base_work_dir, puller_platform, inference_server_binary, model)

                platforms_pulled.add(puller_platform.name)
        finally:
            puller_platform.inference_server_mod.stop_server(base_work_dir, puller_platform, inference_server_binary)

    if config.project.get_config("prepare.podman.machine.enabled"):
        podman_machine.configure_and_start(base_work_dir, force_restart=False)

    if config.project.get_config("prepare.remoting.publish"):
        if config.project.get_config("exec_list.pre_cleanup_ci") is False:
            raise ValueError("Cannot publish the remoting libraries if not preparing from a clean environment")
        if not config.project.get_config("prepare.virglrenderer.enabled"):
            raise ValueError("Cannot publish the remoting libraries if building virglrenderer isn't enabled")
        if "podman/llama_cpp/remoting" not in platforms_to_build_str:
            raise ValueError("Cannot publish the remoting libraries if podman/llama_cpp/remoting isn't built")

        prepare_release.create_remoting_tarball(base_work_dir)

    return 0


def cleanup_llm_load_test(base_work_dir):
    dest = base_work_dir / "llm-load-test"

    if not remote_access.exists(dest):
        logging.info(f"{dest} does not exists, nothing to remove.")
        return

    logging.info(f"Removing {dest} ...")
    remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -rf {dest}")


def prepare_llm_load_test(base_work_dir):
    dest = base_work_dir / "llm-load-test"

    if not config.project.get_config("test.llm_load_test.enabled"):
        logging.info("llm-load-test not enabled, not preparing it.")
        return

    if remote_access.exists(dest):
        logging.info(f"{dest} already exists, not cloning it.")
        return

    # running this locally to know llm-load-test is configured in TOPSAIL's repo
    submodule_status = run.run("git submodule status | grep llm-load-test", capture_stdout=True).stdout
    submodule_commit = submodule_status.split()[0].replace("+", "")
    submodule_path = submodule_status.split()[1]
    repo_url= run.run(f"git config --file=.gitmodules submodule.'{submodule_path}'.url", capture_stdout=True).stdout.strip()

    run.run_toolbox(
        "remote", "clone",
        repo_url=repo_url, dest=dest, version=submodule_commit,
        artifact_dir_suffix="__llm_load_test",
    )

    python_bin = config.project.get_config("remote_host.python_bin", "python3")

    if config.project.get_config("prepare.llm_load_test.install_requirements"):
        remote_access.run_with_ansible_ssh_conf(
            base_work_dir,
            f"{python_bin} -m pip install -r {dest}/requirements.txt --user",
        )
    else:
        logging.info("Not installing llm-load-test requirements.")


def cleanup_gguf_models(base_work_dir):
    model_gguf_dir = config.project.get_config("test.model.gguf_dir")
    dest = base_work_dir / model_gguf_dir

    if not remote_access.exists(dest):
        logging.info(f"{dest} does not exists, nothing to remove.")
        return

    # Get the current model(s) to preserve them
    current_model = config.project.get_config("test.model.name")
    current_models_fnames = []

    # `test.model.name` can be a string or a list; normalize to a list.
    if current_model is None:
        current_models = None
    elif isinstance(current_model, list):
        current_models = current_model
    else:
        current_models = [current_model]

    if current_models:
        for model in current_models:
            model_fname = utils.model_to_fname(llama_cpp._model_name(model))
            if remote_access.exists(model_fname):
                current_models_fnames.append(model_fname)
                logging.info(f"Preserving current model: {model_fname}")
            else:
                logging.info(f"Current model not found, won't preserve: {model_fname}")

    # List all files in the GGUF directory
    try:
        files_output = remote_access.run_with_ansible_ssh_conf(base_work_dir, "ls", chdir=dest, capture_stdout=True).stdout.strip()
        if files_output:
            files_to_remove = []
            for file_path in files_output.split('\n'):
                if not file_path.strip():
                    continue
                file_full_path = dest / file_path
                if any(file_full_path == current_fname for current_fname in current_models_fnames):
                    logging.info(f"Skipping current model: {file_path}")
                    continue
                files_to_remove.append(file_path)

            if files_to_remove:
                logging.info(f"Removing {len(files_to_remove)} GGUF model files...")
                for file_path in files_to_remove:
                    remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -f '{dest / file_path}'")
            else:
                logging.info("No GGUF files to remove.")
        else:
            logging.info("No GGUF files found in the directory.")

        # Remove empty directories if any
        remote_access.run_with_ansible_ssh_conf(base_work_dir, f"find {dest} -type d -empty -delete", capture_stdout=True)

    except subprocess.CalledProcessError:
        # If find command fails, fall back to removing the entire directory
        # (unless we have current models to preserve)
        if current_models_fnames:
            logging.warning(f"Could not list GGUF files, but preserving current models: {[str(fname) for fname in current_models_fnames]}")
        else:
            logging.info(f"Removing entire directory {dest} ...")
            remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -rf {dest}")
