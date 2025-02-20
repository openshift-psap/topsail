import os
import pathlib
import logging

from projects.core.library import env, config, run, configure_logging, export
import remote_access

def install_dependencies(base_work_dir, capture_stderr=False):
    if config.project.get_config("remote_host.system") != "darwin": return

    dependencies = " ".join(config.project.get_config("prepare.brew.dependencies"))
    return remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"/opt/homebrew/bin/brew install {dependencies}",
        capture_stderr=capture_stderr,
    )


def capture_dependencies_version(base_work_dir):
    if config.project.get_config("remote_host.system") != "darwin": return

    with env.NextArtifactDir("brew_dependencies"):
        ret = install_dependencies(base_work_dir, capture_stderr=True)

        with open(env.ARTIFACT_DIR / "dependencies.txt", "w") as f:
            print(ret.stderr, file=f)
