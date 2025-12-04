import os
import pathlib
import logging
import tempfile
import json

from projects.core.library import env, config, run, configure_logging, export
from projects.matrix_benchmarking.library import visualize

import podman as podman_mod
import utils, prepare_release

from projects.remote.lib import remote_access

def prepare_test(base_work_dir, platform):
    # nothing to do here
    pass


def _get_binary_path(base_work_dir, platform):
    version = config.project.get_config("prepare.ramalama.repo.version")

    if version == "latest":
        repo_url = config.project.get_config("prepare.ramalama.repo.url")
        version = utils.get_latest_release(repo_url)
        config.project.set_config("prepare.ramalama.repo.version", version)

    dest_base = base_work_dir / "ramalama-ai"

    # don't use 'ramalama' in the base_work_dir, otherwise Python
    # takes it (invalidly) for the package `ramalama` package

    dest_dir = dest_base / f"ramalama-{version.removeprefix('v')}"

    ramalama_path = dest_dir / "bin" / "ramalama"

    return ramalama_path, dest_dir, version


def get_binary_path(base_work_dir, platform):
    error_msg = utils.check_expected_platform(platform, system="podman", inference_server_name="ramalama", needs_podman_machine=True, needs_podman=False)
    if error_msg:
        raise ValueError(f"ramalama.get_binary_path: unexpected platform: {error_msg} :/")

    ramalama_path, _, _  = _get_binary_path(base_work_dir, platform)

    return ramalama_path

def download_ramalama(base_work_dir, dest, version):
    repo_url = config.project.get_config("prepare.ramalama.repo.url")

    kwargs = dict(
        repo_url=repo_url,
        dest=dest,
    )
    if version.startswith("pr-"):
        pr_number = version.removeprefix("pr-")
        kwargs["refspec"] = f"refs/pull/{pr_number}/head"
    else:
        kwargs["version"] = version

    run.run_toolbox(
        "remote", "clone",
        **kwargs,
        artifact_dir_suffix="_ramalama",
        force=True,
    )

    remote_access.run_with_ansible_ssh_conf(base_work_dir, "git show -s --format='%cd%n%s%n%H' --date=format:'%y%m%d.%H%M' > ramalama-commit.info",
                                        chdir=dest)


def build_container_image(base_work_dir, ramalama_path, platform):
    image_name = config.project.get_config("prepare.ramalama.build_image.name")
    registry_path = config.project.get_config("prepare.ramalama.build_image.registry_path")
    image_fullname = get_local_image_name()

    if podman_mod.has_image(base_work_dir, image_fullname):
        logging.info(f"Image {image_fullname} already exist, not rebuilding it.")
        return image_fullname

    chdir = ramalama_path.parent.parent
    system = config.project.get_config("remote_host.system")
    logging.info("Building the ramalama image ...")
    with env.NextArtifactDir(f"build_ramalama_{image_name}_image"):
        cmd = f"env PATH=$PATH:{podman_mod.get_podman_binary(base_work_dir).parent}"

        if system == "linux" and platform.inference_server_flavor == "remoting":
            cmd += f" RAMALAMA_IMAGE_BUILD_REMOTING_BACKEND={config.project.get_config('prepare.ramalama.remoting.backend')}"

        cmd += f" time ./container_build.sh -s build {image_name}"
        cmd += " 2>&1"

        extra_env = dict(
            REGISTRY_PATH=registry_path,
        )

        if config.project.get_config("prepare.ramalama.build_image.name") == "remoting":
            version = config.project.get_config("prepare.llama_cpp.source.repo.version")
            if version.startswith("pr-"):
                pr_number = version.removeprefix("pr-")
                version = f"refs/pull/{pr_number}/head"
            extra_env["LLAMA_CPP_PULL_REF"] = version

            extra_env["LLAMA_CPP_REPO"] = config.project.get_config("prepare.llama_cpp.source.repo.url")

        if config.project.get_config("prepare.ramalama.build_image.debug"):
            extra_env["RAMALAMA_IMAGE_BUILD_DEBUG_MODE"] = "y"

        ret = remote_access.run_with_ansible_ssh_conf(base_work_dir, cmd,
                                                      extra_env=extra_env,
                                                      chdir=chdir, check=False, capture_stdout=True)
        build_log = env.ARTIFACT_DIR / "build.log"
        build_log.write_text(ret.stdout)
        if ret.returncode != 0:
            raise RuntimeError(f"Compilation of the ramalama image failed ... (see {build_log})")

        logging.info(f"ramalama image build logs saved into {build_log}")

    return image_fullname


def get_local_image_name():
    registry_path = config.project.get_config("prepare.ramalama.build_image.registry_path")
    image_name = config.project.get_config("prepare.ramalama.build_image.name")

    return f"{registry_path}/{image_name}:latest"


def get_release_image_name(base_work_dir, platform, build_version):
    _, _, version = _get_binary_path(base_work_dir, platform)

    registry_path = config.project.get_config("prepare.ramalama.build_image.registry_path")
    image_name = config.project.get_config("prepare.ramalama.build_image.name")

    dest_image_name = registry_path + "/" + image_name + f":{version}_apir.{build_version}"

    if config.project.get_config("prepare.ramalama.build_image.debug"):
        dest_image_name += "-debug"

    return dest_image_name


def publish_ramalama_image(base_work_dir, platform, build_version):
    image_name = get_local_image_name()

    podman_mod.login(base_work_dir, "prepare.ramalama.build_image.publish.credentials")

    release_image_name = get_release_image_name(base_work_dir, platform, build_version)

    latest_suffix = ":debug" if config.project.get_config("prepare.ramalama.build_image.debug") \
        else ":latest"
    release_image_latest = release_image_name.rpartition(":")[0] + latest_suffix

    logging.info(f"Pushing the image to {release_image_name} and {release_image_latest}")

    podman_mod.push_image(base_work_dir, image_name, release_image_name)
    podman_mod.push_image(base_work_dir, image_name, release_image_latest)

    return release_image_name


def prepare_binary(base_work_dir, platform):
    ramalama_path, dest, version = _get_binary_path(base_work_dir, platform)

    if version.startswith("pr-") or not remote_access.exists(ramalama_path):
        download_ramalama(base_work_dir, dest, version)
    else:
        logging.info(f"ramalama {platform.name} already exists, not downloading it.")

    remote_access.run_with_ansible_ssh_conf(base_work_dir, "python3 -m pip install --user --break-system-packages jinja2 jsonschema")

    build_image_enabled = config.project.get_config("prepare.ramalama.build_image.enabled")
    if build_image_enabled is True or build_image_enabled == platform.inference_server_flavor:
        build_container_image(base_work_dir, ramalama_path, platform)
    else:
        logging.info(f"ramalama image build not requested.")

    return ramalama_path


def has_model(base_work_dir, ramalama_path, model_name):
    # tell if the model is available locally
    ret = _run(base_work_dir, ramalama_path, "ls --json", check=False, capture_stdout=True)

    if ret.returncode != 0:
        raise ValueError("Ramalama couldn't list the model :/")

    lst = json.loads(ret.stdout)
    for current_model_info in lst:
        current_model_name = current_model_info["name"].partition("://")[-1]
        if current_model_name == model_name:
            return True
        if current_model_name == f"{model_name}:latest":
            return True
        logging.info(f"{current_model_info['name']} != {model_name}")

    return False


def pull_model(base_work_dir, ramalama_path, model_name):
    _run(base_work_dir, ramalama_path, f"pull {model_name} 2>/dev/null")


def start_server(base_work_dir, ramalama_path, stop=False):
    return # nothing to do


def stop_server(base_work_dir, ramalama_path):
    return # nothing to do


def run_model(base_work_dir, platform, ramalama_path, model, unload=False):
    inference_server_port = config.project.get_config("test.inference_server.port")

    commit_date_cmd = remote_access.run_with_ansible_ssh_conf(base_work_dir, f"cat ramalama-commit.info", chdir=ramalama_path.parent.parent, check=False, capture_stdout=True)
    if commit_date_cmd.returncode != 0:
        logging.warning("Couldn't find the Ramalama commit info file ...")
    else:
        logging.warning(f"Ramalama commit info: {commit_date_cmd.stdout}")
        (env.ARTIFACT_DIR / "ramalama-commit.info").write_text(commit_date_cmd.stdout)

    artifact_dir_suffix=None
    if unload:
        logging.info("Unloading the model from ramalama server ...")
        artifact_dir_suffix = "_unload"

    _run_from_toolbox(
        "run_model",
        base_work_dir, platform, ramalama_path, model,
        extra_kwargs=dict(
            unload=unload,
            port=inference_server_port,
            mute_stdout=unload,
            artifact_dir_suffix=artifact_dir_suffix,
        )
    )

    return model

def unload_model(base_work_dir, platform, ramalama_path, model):
    run_model(base_work_dir, platform, ramalama_path, model, unload=True)


def run_benchmark(base_work_dir, platform, ramalama_path, model):
    return _run_from_toolbox("run_bench", base_work_dir, platform, ramalama_path, model)


def _get_env(base_work_dir, ramalama_path):
    env = dict(
        PYTHONPATH=ramalama_path.parent.parent,
        RAMALAMA_CONTAINER_ENGINE=podman_mod.get_podman_binary(base_work_dir),
    ) | podman_mod.get_podman_env(base_work_dir)

    system = config.project.get_config("remote_host.system")
    platform = utils.parse_platform(config.project.get_config("test.platform"))

    if system == "linux" and platform.inference_server_flavor == "remoting":
        env |= prepare_release.get_linux_remoting_host_env(base_work_dir)

    return env


def _run(base_work_dir, ramalama_path, ramalama_cmd, *, check=False, capture_stdout=False, capture_stderr=False):
    extra_env = _get_env(base_work_dir, ramalama_path)

    return remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"{ramalama_path} {ramalama_cmd}",
        check=check, capture_stdout=capture_stdout, capture_stderr=capture_stderr,
        extra_env=extra_env,
    )


def _run_from_toolbox(ramalama_cmd, base_work_dir, platform, ramalama_path, model, extra_kwargs={}):
    env_str = " ".join([f"{k}='{v}'" for k, v in _get_env(base_work_dir, ramalama_path).items()])

    want_gpu = platform.want_gpu
    device = config.project.get_config("prepare.podman.container.device") \
        if want_gpu else "none"

    if config.project.get_config("prepare.ramalama.build_image.enabled"):
        image_name = config.project.get_config("prepare.ramalama.build_image.name")
        registry_path = config.project.get_config("prepare.ramalama.build_image.registry_path")
        image = f"{registry_path}/{image_name}:latest"
    elif version := config.project.get_config("prepare.ramalama.repo.version"):
        version = version.removeprefix("v")
        image = f"quay.io/ramalama/ramalama:{version}"
    else:
        image = None

    extra_extra_kwargs = {} # don't modify extra_kwargs here

    system = config.project.get_config("remote_host.system")
    # if remoting is enabled, always use the krun flavor (not only for the remoting platform)
    if system == "linux" and config.project.get_config("prepare.podman.machine.remoting_env.enabled"):
        extra_extra_kwargs["oci_runtime"] = "krun"

    run.run_toolbox(
        "mac_ai", f"remote_ramalama_{ramalama_cmd}",
        base_work_dir=base_work_dir,
        path=ramalama_path,
        device=device,
        env=env_str,
        model_name=model,
        image=image,
        **(extra_kwargs | extra_extra_kwargs),
    )


def cleanup_files(base_work_dir):
    dest = base_work_dir / "ramalama-ai"

    if not remote_access.exists(dest):
        logging.info(f"{dest} does not exists, nothing to remove.")
        return

    logging.info(f"Removing {dest} ...")
    remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -r {dest}")


def cleanup_models(base_work_dir):
    dest = base_work_dir / ".local/share/ramalama"

    if not remote_access.exists(dest):
        logging.info(f"{dest} does not exists, nothing to remove.")
        return

    logging.info(f"Removing {dest} ...")
    remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -r {dest}")
