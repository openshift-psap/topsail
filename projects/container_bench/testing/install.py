
from projects.core.library import config
import remote_access


def dependencies(base_work_dir, capture_stderr=False):
    if config.project.get_config("remote_host.system", print=False) == "darwin":
        if not config.project.get_config("prepare.brew.install_dependencies", print=False):
            return None

        dependencies = " ".join(config.project.get_config("prepare.brew.dependencies"))

        return remote_access.run_with_ansible_ssh_conf(
            base_work_dir,
            f"/opt/homebrew/bin/brew install {dependencies}",
            capture_stderr=capture_stderr,
        )

    if config.project.get_config("remote_host.system", print=False) == "linux":
        if not config.project.get_config("prepare.dnf.install_dependencies", print=False):
            return None
        if config.project.get_config("prepare.dnf.enable_docker_repo", print=False):
            docker_repo_url = "https://download.docker.com/linux/fedora/docker-ce.repo"
            docker_repo_cmd = f"sudo dnf config-manager addrepo --overwrite --from-repofile={docker_repo_url}"
            remote_access.run_with_ansible_ssh_conf(
                base_work_dir,
                docker_repo_cmd,
                capture_stderr=capture_stderr,
            )

        dependencies = " ".join(config.project.get_config("prepare.dnf.dependencies"))

        return remote_access.run_with_ansible_ssh_conf(
            base_work_dir,
            f"sudo dnf install -y {dependencies}",
            capture_stderr=capture_stderr,
        )

    # TODO implement other systems if needed
    return None
