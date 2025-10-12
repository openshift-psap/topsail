import remote_access
from config_manager import ConfigManager, SystemType


def dependencies(base_work_dir, capture_stderr=False):
    system_type = ConfigManager.get_system_type()

    if system_type == SystemType.DARWIN:
        brew_config = ConfigManager.get_brew_config()
        if not brew_config['install_dependencies']:
            return None

        dependencies = " ".join(brew_config['dependencies'])

        return remote_access.run_with_ansible_ssh_conf(
            base_work_dir,
            f"/opt/homebrew/bin/brew install {dependencies}",
            capture_stderr=capture_stderr,
        )

    if system_type == SystemType.LINUX:
        dnf_config = ConfigManager.get_dnf_config()
        if not dnf_config['install_dependencies']:
            return None
        if dnf_config['enable_docker_repo']:
            docker_repo_url = "https://download.docker.com/linux/fedora/docker-ce.repo"
            docker_repo_cmd = f"sudo dnf config-manager addrepo --overwrite --from-repofile={docker_repo_url}"
            remote_access.run_with_ansible_ssh_conf(
                base_work_dir,
                docker_repo_cmd,
                capture_stderr=capture_stderr,
            )

        dependencies = " ".join(dnf_config['dependencies'])

        return remote_access.run_with_ansible_ssh_conf(
            base_work_dir,
            f"sudo dnf install -y {dependencies}",
            capture_stderr=capture_stderr,
        )

    return None
