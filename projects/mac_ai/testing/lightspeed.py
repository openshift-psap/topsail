import os
import pathlib
import logging
import tempfile
import json

from projects.core.library import env, config, run, configure_logging, export
from projects.matrix_benchmarking.library import visualize

import podman as podman_mod
import utils
from projects.remote.lib import remote_access


def prepare_test(base_work_dir, platform):
    # nothing to do here
    pass


def prepare_binary(base_work_dir, platform):
    installer_image(base_work_dir, pull=True)

    remote_access.run_with_ansible_ssh_conf(base_work_dir, f"rm -rf '{base_work_dir}/.config/rhel-cla'")

    bin_dir = installer_run(base_work_dir, "install")

    podman_cmd = podman_mod.get_podman_command()

    # /!\ podzman typo is on purpose to avoid sed to rewrite podman multiple times (over multiple executions)
    remote_access.write(bin_dir / "podzman", f'#!/usr/bin/env bash\n{podman_cmd} "\$@"\n')
    remote_access.run_with_ansible_ssh_conf(base_work_dir, f"chmod u+x '{bin_dir / 'podzman'}'")

    remote_access.run_with_ansible_ssh_conf(base_work_dir, f"sed 's+podman+{bin_dir / 'podzman'}+g' '{base_work_dir}/.config/rhel-cla/rhel-cla-runner.sh' > '{base_work_dir}/.config/rhel-cla/rhel-cla-runner.new.sh'")
    remote_access.run_with_ansible_ssh_conf(base_work_dir, f"mv '{base_work_dir}/.config/rhel-cla/rhel-cla-runner.new.sh' '{base_work_dir}/.config/rhel-cla/rhel-cla-runner.sh'")

    return bin_dir / "rhel-cla"


def get_binary_path(base_work_dir, platform):
    return base_work_dir / ".local" / "bin" / "rhel-cla"


def installer_image(base_work_dir, pull=False, rm=False):
    image_name = get_image_name()
    if not podman_mod.has_image(base_work_dir, image_name):
        if pull:
            creds = config.project.get_config("prepare.lightspeed.installer.credentials", handled_secretly=True)
            podman_mod.write_authfile(base_work_dir, creds)

            podman_mod.pull_image(base_work_dir, image_name)
            return True
        return False
    else:
        if rm:
            podman_mod.rm_image(base_work_dir, image_name)
            return False
        return True


def installer_run(base_work_dir, command):
    base_dir = base_work_dir

    config_dir = base_dir / ".config"
    remote_access.mkdir(config_dir)

    bin_dir = base_dir / ".local/bin"
    remote_access.mkdir(bin_dir)

    volumes = {
        str(config_dir): "/config",
        str(bin_dir): "/config/.local/bin",
    }

    podman_mod.run_container(base_work_dir, get_image_name(), volumes=volumes, command=command)

    return bin_dir


def has_model(base_work_dir, lightspeed_path, model_name):
    return True


def pull_model(base_work_dir, lightspeed_path, model_name):
    if not model_name.startswith("/models/"):
        raise ValueError("Lightspeed can only be tested with the lightspeed model")

    logging.info("Nothing to do ...")

    return


def start_server(base_work_dir, lightspeed_path):
    with env.NextArtifactDir("lightspeed_start_server"):
        creds = config.project.get_config("prepare.lightspeed.installer.credentials", handled_secretly=True)
        podman_mod.write_authfile(base_work_dir, creds)

        inspect = podman_mod.inspect_image(base_work_dir, get_image_name())
        with open(env.ARTIFACT_DIR / "inspect-image.json", "w") as f:
            json.dump(inspect, indent=4, fp=f)

        remote_access.run_with_ansible_ssh_conf(base_work_dir, f"bash {lightspeed_path} start")


def stop_server(base_work_dir, lightspeed_path):
    remote_access.run_with_ansible_ssh_conf(base_work_dir, f"bash {lightspeed_path} stop")


def run_model(base_work_dir, platform, lightspeed_path, model):
    pass # nothing to do


def unload_model(base_work_dir, platform, lightspeed_path, model):
    pass # nothing to do


def run_benchmark(base_work_dir, platform, lightspeed_path, model):
    with env.NextArtifactDir("lightspeed_run_bench"):
        remote_access.mkdir(env.ARTIFACT_DIR / "artifacts")
        container_name = config.project.get_config("prepare.lightspeed.runtime.container_names.model")
        remote_access.run_with_ansible_ssh_conf(base_work_dir,
                                                      f"{podman_mod.get_podman_command()} exec '{container_name}' llama-bench --verbose -m '{model}' > '{env.ARTIFACT_DIR}/artifacts/llama-bench.log' 2>&1")

    pass


def cleanup_files(base_work_dir):
    installer_image(base_work_dir, rm=True)

    remote_access.run_with_ansible_ssh_conf(
        base_work_dir, f"rm -rf '{base_work_dir}/.config/rhel-cla'"
    )
    remote_access.run_with_ansible_ssh_conf(
        base_work_dir, f"rm -f '{base_work_dir}/.local/bin/rhel-cla' '{base_work_dir}/.local/bin/podzman'"
    )


def cleanup_images(base_work_dir):
    podman_mod.rm_image(base_work_dir, get_image_name())


def get_image_name():
    image = config.project.get_config("prepare.lightspeed.installer.image")
    version = config.project.get_config("prepare.lightspeed.installer.version")

    return f"{image}:{version}"
