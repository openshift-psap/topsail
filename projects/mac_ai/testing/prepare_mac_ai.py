import os
import pathlib
import logging
import tarfile

from projects.core.library import env, config, run, configure_logging, export
from projects.matrix_benchmarking.library import visualize

import prepare_llama_cpp, utils, remote_access, podman_machine, brew, podman, prepare_virglrenderer
import llama_cpp, ollama, ramalama

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
CRC_MAC_AI_SECRET_PATH = pathlib.Path(os.environ.get("CRC_MAC_AI_SECRET_PATH", "/env/CRC_MAC_AI_SECRET_PATH/not_set"))

PREPARE_INFERENCE_SERVERS = dict(
    llama_cpp=prepare_llama_cpp,
    ollama=ollama,
    ramalama=ramalama,
)

INFERENCE_SERVERS = dict(
    llama_cpp=llama_cpp,
    ollama=ollama,
    ramalama=ramalama,
)


REMOTING_FRONTEND_PLATFORM = "podman/llama_cpp/remoting"
REMOTING_BACKEND_PLATFORM = "macos/llama_cpp/remoting"
RAMALAMA_REMOTING_PLATFORM = "podman/ramalama/remoting"

def cleanup():
    base_work_dir = remote_access.prepare()

    if config.project.get_config("cleanup.images.llama_cpp"):
        is_running = podman_machine.is_running(base_work_dir)
        if is_running is None:
            logging.warning("Podman machine doesn't exist.")
        elif not is_running:
            if podman_machine.start(base_work_dir, use_remoting=False):
                is_running = True
            else:
                logging.warning(f"Could not start podman machine, cannot check/move the {local_image_name} image ...")
                is_running = None

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

    # ***

    if config.project.get_config("cleanup.podman_machine.delete"):
        is_running = podman_machine.is_running(base_work_dir)
        if is_running:
            podman_machine.stop(base_work_dir)
        if is_running is not None:
            podman_machine.rm(base_work_dir)
            if config.project.get_config("cleanup.podman_machine.reset"):
                podman_machine.reset(base_work_dir)

    if config.project.get_config("cleanup.files.podman"):
        podman.cleanup(base_work_dir)

    if config.project.get_config("cleanup.files.virglrenderer"):
        prepare_virglrenderer.cleanup(base_work_dir)


    return 0


def prepare():
    base_work_dir = remote_access.prepare()
    if not config.project.get_config("prepare.prepare_only_inference_server"):
        if config.project.get_config("prepare.podman.repo.enabled"):
            podman.prepare_from_gh_binary(base_work_dir)
            podman.prepare_gv_from_gh_binary(base_work_dir)

        brew.install_dependencies(base_work_dir)

        prepare_llm_load_test(base_work_dir)

        prepare_virglrenderer.prepare(base_work_dir)

        podman_machine.configure_and_start(base_work_dir, force_restart=True)

    platforms_to_build_str = config.project.get_config("prepare.platforms.to_build")
    if not platforms_to_build_str:
        platforms_to_build_str = config.project.get_config("test.platform")

    if not isinstance(platforms_to_build_str, list):
        platforms_to_build_str = [platforms_to_build_str]

    if (REMOTING_FRONTEND_PLATFORM in platforms_to_build_str and
        REMOTING_BACKEND_PLATFORM not in platforms_to_build_str):
        platforms_to_build_str.append(REMOTING_BACKEND_PLATFORM)

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
    for platform in platforms_to_build:
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
            puller_platform.inference_server_mod.start_server(base_work_dir, inference_server_binary)
            for model in models if isinstance(models, list) else [models]:
                config.project.set_config("test.model.name", model)

                if puller_platform.inference_server_mod.has_model(base_work_dir, inference_server_binary, model):
                    continue

                puller_platform.inference_server_mod.pull_model(base_work_dir, inference_server_binary, model)

                platforms_pulled.add(puller_platform.name)
        finally:
            puller_platform.inference_server_mod.stop_server(base_work_dir, inference_server_binary)

    if config.project.get_config("prepare.podman.machine.enabled"):
        podman_machine.configure_and_start(base_work_dir, force_restart=False)

    if config.project.get_config("prepare.remoting.publish"):
        #if not config.project.get_config("exec_list.pre_cleanup_ci"):
        #    raise ValueError("Cannot publish the remoting libraries if not preparing from a clean environment")
        if not config.project.get_config("prepare.virglrenderer.enabled"):
            raise ValueError("Cannot publish the remoting libraries if building virglrenderer isn't enabled")
        if "podman/llama_cpp/remoting" not in platforms_to_build_str:
            raise ValueError("Cannot publish the remoting libraries if podman/llama_cpp/remoting isn't built")

        prepare_remoting_tarball(base_work_dir)

    return 0


def prepare_remoting_tarball(base_work_dir):
    virglrenderer_lib = prepare_virglrenderer.get_dyld_library_path(base_work_dir, with_lib=True)

    if not remote_access.exists(virglrenderer_lib):
        raise ValueError(f"Cannot publish the remoting libraries, {virglrenderer_lib} does not exist")

    llama_remoting_backend_build_dir = prepare_llama_cpp.get_remoting_build_dir(base_work_dir)
    apir_backend_lib = llama_remoting_backend_build_dir / config.project.get_config("prepare.podman.machine.remoting_env.apir_lib.name")
    if not remote_access.exists(apir_backend_lib):
        raise ValueError(f"Cannot publish the remoting libraries, {apir_backend_lib} does not exist")

    llama_cpp_backend_lib = llama_remoting_backend_build_dir / config.project.get_config("prepare.podman.machine.remoting_env.ggml_lib.name")
    if not remote_access.exists(llama_cpp_backend_lib):
        raise ValueError(f"Cannot publish the remoting libraries, {llama_cpp_backend_lib} does not exist")

    virglrenderer_branch = config.project.get_config("prepare.virglrenderer.repo.branch")
    if not virglrenderer_branch.startswith("v"):
        raise ValueError("Cannot publish the remoting libraries, virglrenderer not built from a released version")

    with env.NextArtifactDir("build_remoting_tarball"):
        return build_remoting_tarball(base_work_dir, virglrenderer_lib, llama_cpp_backend_lib, apir_backend_lib)


def build_remoting_tarball(base_work_dir, virglrenderer_lib, llama_cpp_backend_lib, apir_backend_lib):
    llama_cpp_version = config.project.get_config("prepare.llama_cpp.source.repo.version")
    llama_cpp_url = config.project.get_config("prepare.llama_cpp.source.repo.url")

    virglrenderer_version = config.project.get_config("prepare.virglrenderer.repo.branch")
    virglrenderer_url = config.project.get_config("prepare.virglrenderer.repo.url")

    logging.info(f"Preparing the API remoting data into {env.ARTIFACT_DIR} ...")
    tarball_dir = env.ARTIFACT_DIR / f"llama_cpp-api_remoting-{llama_cpp_version}"
    tarball_dir.mkdir()

    virglrenderer_dest = tarball_dir / "virglrenderer" / virglrenderer_lib.name
    virglrenderer_dest.parent.mkdir()

    logging.info(f"Preparing {virglrenderer_dest.name} ...")
    virglrenderer = remote_access.run_with_ansible_ssh_conf(base_work_dir, f"cat '{virglrenderer_lib}'", capture_stdout=True, decode_stdout=False)
    virglrenderer_dest.write_bytes(virglrenderer.stdout)

    virglrenderer_src_dir = prepare_virglrenderer.get_build_dir(base_work_dir) / ".." / "src"
    virglrenderer_git_show_cmd = remote_access.run_with_ansible_ssh_conf(base_work_dir, f"git -C '{virglrenderer_src_dir}' show", capture_stdout=True)
    virglrenderer_git_revparse_cmd = remote_access.run_with_ansible_ssh_conf(base_work_dir, f"git -C '{virglrenderer_src_dir}' rev-parse HEAD", capture_stdout=True)
    virglrenderer_git_show_file = virglrenderer_dest.parent / "git-commit.txt"
    virglrenderer_git_show_file.write_text(virglrenderer_git_show_cmd.stdout)

    virglrenderer_version_file = virglrenderer_dest.parent / "version.txt"
    virglrenderer_version_file.write_text(f"{virglrenderer_url}/-/tree/{virglrenderer_git_revparse_cmd.stdout.strip()} ({virglrenderer_version})")

    llama_cpp_backend_dest = tarball_dir / "llama.cpp" / llama_cpp_backend_lib.name
    llama_cpp_backend_dest.parent.mkdir()

    llama_cpp_src_dir = prepare_llama_cpp.get_source_dir(base_work_dir)
    llama_cpp_git_show_cmd = remote_access.run_with_ansible_ssh_conf(base_work_dir, f"git -C '{llama_cpp_src_dir}' show", capture_stdout=True)
    llama_cpp_git_revparse_cmd = remote_access.run_with_ansible_ssh_conf(base_work_dir, f"git -C '{llama_cpp_src_dir}' rev-parse HEAD", capture_stdout=True)
    llama_cpp_git_show_file = llama_cpp_backend_dest.parent / "git-commit.txt"
    llama_cpp_git_show_file.write_text(llama_cpp_git_show_cmd.stdout)

    llama_cpp_version_file = llama_cpp_backend_dest.parent / "version.txt"
    llama_cpp_version_file.write_text(f"{llama_cpp_url}/commit/{llama_cpp_git_revparse_cmd.stdout.strip()} ({llama_cpp_version})")

    logging.info(f"Preparing {virglrenderer_dest.name} ...")
    llama_cpp_backend = remote_access.run_with_ansible_ssh_conf(base_work_dir, f"cat '{llama_cpp_backend_lib}'", capture_stdout=True, decode_stdout=False)
    llama_cpp_backend_dest.write_bytes(llama_cpp_backend.stdout)

    apir_backend_dest = llama_cpp_backend_dest.parent / apir_backend_lib.name
    logging.info(f"Preparing {apir_backend_dest.name} ...")
    apir_backend = remote_access.run_with_ansible_ssh_conf(base_work_dir, f"cat '{apir_backend_lib}'", capture_stdout=True, decode_stdout=False)
    apir_backend_dest.write_bytes(apir_backend.stdout)

    script_file = pathlib.Path("projects/mac_ai/testing/scripts/podman_start_machine.api_remoting.sh")
    script_file_dest = tarball_dir / script_file.name
    script_file_dest.write_text(script_file.read_text())

    if config.project.get_config("prepare.ramalama.build_image.publish.enabled"):
        ramalama_cmd_dest = tarball_dir / "ramalama-info.txt"
        registry_path = config.project.get_config("prepare.ramalama.build_image.registry_path")
        image_name = config.project.get_config("prepare.ramalama.build_image.name")
        ramalama_image = f"{registry_path}/{image_name}:{llama_cpp_version}"

        _, ramalama_src_dir, _ = ramalama._get_binary_path(base_work_dir, RAMALAMA_REMOTING_PLATFORM)

        ramalama_git_show_cmd = remote_access.run_with_ansible_ssh_conf(base_work_dir, f"git -C '{ramalama_src_dir}' show", capture_stdout=True)
        ramalama_git_revparse_cmd = remote_access.run_with_ansible_ssh_conf(base_work_dir, f"git -C '{ramalama_src_dir}' rev-parse HEAD", capture_stdout=True)

        ramalama_repo_url = config.project.get_config("prepare.ramalama.repo.url")

        ramalama_cmd_dest.write_text(f"""\
RamaLama image  : {ramalama_image}
RamaLama command: ramalama --image {ramalama_image} ...
RamaLama commit : {ramalama_repo_url}/commit/{ramalama_git_revparse_cmd.stdout.strip()}

{ramalama_git_show_cmd.stdout.strip()}
""")

    tarball_file = env.ARTIFACT_DIR / f"llama_cpp-api_remoting-{llama_cpp_version}.tar.gz"
    with tarfile.open(tarball_file, "w:gz") as tar:
        tar.add(virglrenderer_dest, virglrenderer_dest.relative_to(env.ARTIFACT_DIR))
        tar.add(llama_cpp_backend_dest, llama_cpp_backend_dest.relative_to(env.ARTIFACT_DIR))
        tar.add(apir_backend_dest, apir_backend_dest.relative_to(env.ARTIFACT_DIR))

        tar.add(script_file, script_file_dest.relative_to(env.ARTIFACT_DIR))
        tar.add(virglrenderer_git_show_file, virglrenderer_git_show_file.relative_to(env.ARTIFACT_DIR))
        tar.add(llama_cpp_git_show_file, llama_cpp_git_show_file.relative_to(env.ARTIFACT_DIR))

        tar.add(virglrenderer_version_file, virglrenderer_version_file.relative_to(env.ARTIFACT_DIR))
        tar.add(llama_cpp_version_file, llama_cpp_version_file.relative_to(env.ARTIFACT_DIR))

        if config.project.get_config("prepare.ramalama.build_image.publish.enabled"):
            tar.add(ramalama_cmd_dest, ramalama_cmd_dest.relative_to(env.ARTIFACT_DIR))

    logging.info(f"Saved {tarball_file} !")


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

    logging.info(f"Removing {dest} ...")
    remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -r {dest}")
