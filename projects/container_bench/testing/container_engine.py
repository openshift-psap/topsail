import remote_access
import json
import logging

from projects.core.library import config


def get_podman_binary(base_work_dir):
    if config.project.get_config("prepare.podman.repo.enabled", print=False):
        version = config.project.get_config("prepare.podman.repo.version", print=False)
        podman_bin = base_work_dir / f"podman-{version}" / "usr" / "bin" / "podman"
    else:
        podman_bin = config.project.get_config("remote_host.podman_bin", print=False) or "podman"

    return podman_bin


class ContainerEngine:
    def __init__(self, engine):
        self.engine = engine
        if self.engine not in ["podman", "docker"]:
            raise ValueError(f"Unsupported container engine: {self.engine}")
        self.base_work_dir = remote_access.prepare()
        self.engine_binary = None
        if self.engine == "podman":
            self.engine_binary = get_podman_binary(self.base_work_dir)
        elif self.engine == "docker":
            self.engine_binary = config.project.get_config("remote_host.docker.docker_bin", print=False) or "docker"

    def get_env(self):
        env_ = dict(HOME=self.base_work_dir)
        if self.engine == "docker":
            return env_

        if config.project.get_config("prepare.podman.machine.enabled", print=False):
            env_ |= config.project.get_config("prepare.podman.machine.env", print=False)

        return env_

    def get_command(self):
        cmd = self.engine_binary
        if self.engine == "docker":
            return cmd

        podman_env = self.get_env()

        if config.project.get_config("prepare.podman.machine.enabled", print=False):
            machine_name = config.project.get_config("prepare.podman.machine.name", print=False)
            cmd = f"{cmd} --connection '{machine_name}'"

        env_values = " ".join(f"'{k}={v}'" for k, v in (podman_env).items())
        env_cmd = f"env {env_values}"

        cmd = f"{env_cmd} {cmd}"

        return cmd

    def cleanup(self):
        ret = remote_access.run_with_ansible_ssh_conf(
            self.base_work_dir,
            f"{self.get_command()} system prune -a -f",
            check=False,
            capture_stdout=True,
            capture_stderr=True,
        )

        return ret.returncode == 0

    def rm_image(self, image):
        ret = remote_access.run_with_ansible_ssh_conf(
            self.base_work_dir,
            f"{self.get_command()} image rm {image}",
            check=False,
            capture_stdout=True,
            capture_stderr=True,
        )

        return ret.returncode == 0

    def pull_image(self, image):
        ret = remote_access.run_with_ansible_ssh_conf(
            self.base_work_dir,
            f"{self.get_command()} pull {image}",
            check=True,
            capture_stdout=True,
            capture_stderr=True,
        )
        return ret.returncode == 0


class PodmanMachine:
    def __init__(self):
        self.machine_name = config.project.get_config("prepare.podman.machine.name", print=False)
        self.base_work_dir = remote_access.prepare()

    def get_env(self):
        env_ = dict(HOME=self.base_work_dir)
        if config.project.get_config("prepare.podman.machine.enabled", print=False):
            env_ |= config.project.get_config("prepare.podman.machine.env", print=False)

        return env_

    def get_cmd_env(self):
        env_values = " ".join(f"'{k}={v}'" for k, v in (self.get_env()).items())
        env_cmd = f"env {env_values}"

        return env_cmd

    def configure_and_start(self, force_restart=True, configure=False):
        machine_state = self.inspect()
        if not machine_state:
            self.init()
            machine_state = self.inspect()
        was_stopped = machine_state[0]["State"] == "stopped"

        if force_restart and not was_stopped:
            if config.project.get_config("prepare.podman.machine.force_configuration"):
                self.stop()
                was_stopped = True

        if not was_stopped:
            logging.info("podman machine already running. Skipping the configuration part.")
            return

        if configure:
            self.configure()

        self.start()

        machine_state = self.inspect()
        if not machine_state:
            msg = "Podman machine failed to start :/"
            logging.error(msg)
            raise RuntimeError(msg)

        if config.project.get_config("prepare.podman.machine.set_default"):
            name = config.project.get_config("prepare.podman.machine.name", print=False)
            remote_access.run_with_ansible_ssh_conf(
                self.base_work_dir,
                f"{self.get_cmd_env()} {get_podman_binary(self.base_work_dir)} system connection default {name}"
            )

    def configure(self):
        name = config.project.get_config("prepare.podman.machine.name", print=False)
        configuration = config.project.get_config("prepare.podman.machine.configuration")
        config_str = " ".join(f"--{k}={v}" for k, v in configuration.items())

        remote_access.run_with_ansible_ssh_conf(
            self.base_work_dir,
            f"{self.get_cmd_env()} {get_podman_binary(self.base_work_dir)} machine set {config_str} {name}"
        )

    def init(self):
        cmd = f"{get_podman_binary(self.base_work_dir)} machine init {self.machine_name} --rootful"
        cmd = f"{self.get_cmd_env()} {cmd}"
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)

    def start(self):
        cmd = f"{self.get_cmd_env()} {get_podman_binary(self.base_work_dir)} machine start {self.machine_name}"
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)

    def stop(self):
        cmd = f"{self.get_cmd_env()} {get_podman_binary(self.base_work_dir)} machine stop {self.machine_name}"
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)

    def rm(self):
        cmd = f"{self.get_cmd_env()} {get_podman_binary(self.base_work_dir)} machine rm {self.machine_name} --force"
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)

    def reset(self):
        cmd = f"{self.get_cmd_env()} {get_podman_binary(self.base_work_dir)} machine reset --force"
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)

    def is_running(self):
        machine_state = self.inspect()
        if not machine_state:
            return None

        return machine_state[0]["State"] != "stopped"

    def inspect(self):
        cmd = f"{self.get_cmd_env()} {get_podman_binary(self.base_work_dir)} machine inspect {self.machine_name}"
        inspect_cmd = remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd, capture_stdout=True, check=False)
        if inspect_cmd.returncode != 0:
            if "VM does not exist" in inspect_cmd.stdout:
                logging.info("podman_machine: inspect: VM does not exist")
            else:
                logging.error(f"podman_machine: inspect: unhandled status: {inspect_cmd.stdout.strip()}")
            return None

        return json.loads(inspect_cmd.stdout)


class DockerDesktopMachine:
    # Requires Docker Desktop to be installed and running on the remote Mac.
    # Aka testing user must be logged in to the system. And home_is_base_work_dir: false
    def __init__(self):
        self.base_work_dir = remote_access.prepare()
        # cmd = f"ln -Fs {self.base_work_dir / '../.docker'} {self.base_work_dir / '.docker'}"
        # remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)

    def start(self):
        cmd = "docker desktop start"
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)

    def stop(self):
        cmd = "docker desktop stop"
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)

    def is_running(self):
        cmd = "docker desktop status"
        result = remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd, capture_stdout=True, check=False)
        if result.returncode != 0:
            logging.error(f"Docker Desktop status check failed: {result.stdout.strip()}")
            return None

        return "running" in result.stdout.lower()
