import os
import pathlib
import logging
import tempfile
import json

from projects.core.library import env, config, run, configure_logging, export
from projects.matrix_benchmarking.library import visualize

import podman as podman_mod
import remote_access, utils


def prepare_test(base_work_dir, platform):
    # nothing to do here
    pass


def _get_binary_path(base_work_dir, platform):
    git_ref = config.project.get_config("prepare.ramalama.repo.git_ref")
    version = config.project.get_config("prepare.ramalama.repo.version")

    if git_ref and version:
        raise ValueError(f"Cannot have Ramalama git_ref={git_ref} and version={version} set together.")

    if version == "latest":
        repo_url = config.project.get_config("prepare.ramalama.repo.url")
        version = utils.get_latest_release(repo_url)
        config.project.set_config("prepare.ramalama.repo.version", version)

    system_file = f"{version}.zip"

    dest_base = base_work_dir / "ramalama-ai"
    if version:
        # don't use 'ramalama' in the base_work_dir, otherwise Python
        # takes it (invalidly) for the package `ramalama` package
        dest = dest_base / system_file
        dest_dir = dest.parent / f"ramalama-{version.removeprefix('v')}"
    else:
        dest = dest_dir = dest_base / f"ramalama-{git_ref}"

    ramalama_path =  dest_dir / "bin" / "ramalama"
    return ramalama_path, dest, (version, git_ref)


def get_binary_path(base_work_dir, platform):
    error_msg = utils.check_expected_platform(platform, system="podman", inference_server_name="ramalama", needs_podman_machine=True, needs_podman=False)
    if error_msg:
        raise ValueError(f"ramalama.get_binary_path: unexpected platform: {error_msg} :/")

    ramalama_path, _, _  = _get_binary_path(base_work_dir, platform)

    return ramalama_path

def download_ramalama(base_work_dir, dest, version, git_ref):
    repo_url = config.project.get_config("prepare.ramalama.repo.url")

    if version:
        source = "/".join([
            repo_url,
            "archive/refs/tags",
            f"{version}.zip",
        ])
        run.run_toolbox(
            "remote", "download",
            source=source, dest=dest,
            tarball=True,
        )
    else:
        kwargs = dict(
            repo_url=repo_url,
            dest=dest,
        )
        if git_ref.startswith("pr-"):
            pr_number = git_ref.removeprefix("pr-")
            kwargs["refspec"] = f"refs/pull/{pr_number}/head"
        else:
            kwargs["refspec"] = git_ref

        run.run_toolbox(
            "remote", "clone",
            **kwargs,
            artifact_dir_suffix="_llama_cpp",
        )

        remote_access.run_with_ansible_ssh_conf(base_work_dir, f"git show -s --format='%cd%n%s%n%H' --date=format:'%y%m%d.%H%M' > ramalama-commit.info", cwd=dest)


def prepare_binary(base_work_dir, platform):
    ramalama_path, dest, (version, git_ref) = _get_binary_path(base_work_dir, platform)
    system_file = dest.name

    if not remote_access.exists(ramalama_path):
        download_ramalama(base_work_dir, dest, version, git_ref)
    else:
        logging.info(f"ramalama {platform.name} already exists, not downloading it.")

    if config.project.get_config("prepare.ramalama.build_image.enabled"):
        image_name = config.project.get_config("prepare.ramalama.build_image.name")
        chdir = ramalama_path.parent.parent

        with env.NextArtifactDir(f"build_ramalama_{image_name}_image"):
            cmd = f"env PATH=$PATH:{podman_mod.get_podman_binary(base_work_dir).parent}"
            cmd += f" time ./container_build.sh build {image_name}"
            cmd += f" 2>&1"

            ret = remote_access.run_with_ansible_ssh_conf(base_work_dir, cmd,
                                                          chdir=chdir, check=False, capture_stdout=True)
            build_log = env.ARTIFACT_DIR / "build.log"
            build_log.write_text(ret.stdout)
            if ret.returncode != 0:
                raise RuntimeError("Compilation of the ramalama image failed ...")

            logging.info(f"ramalama image build logs saved into {build_log}")
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

    if config.project.get_config("prepare.ramalama.repo.git_ref"):
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
    return dict(
        PYTHONPATH=ramalama_path.parent.parent,
        RAMALAMA_CONTAINER_ENGINE=podman_mod.get_podman_binary(base_work_dir),
    ) | podman_mod.get_podman_env(base_work_dir)


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
        if want_gpu else "/dev/null"

    if config.project.get_config("prepare.ramalama.build_image.enabled"):
        image_name = config.project.get_config("prepare.ramalama.build_image.name")
        image = f"quay.io/ramalama/{image_name}:latest"
    elif version := config.project.get_config("prepare.ramalama.repo.version"):
        version = version.removeprefix("v")
        image = f"quay.io/ramalama/ramalama:{version}"
    else:
        image = None

    run.run_toolbox(
        "mac_ai", f"remote_ramalama_{ramalama_cmd}",
        base_work_dir=base_work_dir,
        path=ramalama_path,
        device=device,
        env=env_str,
        model_name=model,
        image=image,
        **extra_kwargs,
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
