
from projects.core.library import config
import remote_access


def dependencies(base_work_dir, capture_stderr=False):
    if config.project.get_config("remote_host.system") == "darwin":
        if not config.project.get_config("prepare.brew.install_dependencies"):
            return None

        dependencies = " ".join(config.project.get_config("prepare.brew.dependencies"))

        return remote_access.run_with_ansible_ssh_conf(
            base_work_dir,
            f"/opt/homebrew/bin/brew install {dependencies}",
            capture_stderr=capture_stderr,
        )

    # TODO implement other systems if needed
    return None
