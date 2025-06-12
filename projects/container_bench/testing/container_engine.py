import remote_access
import json
import logging

from projects.core.library import config


class container_engine:
    def __init__(self, engine):
        self.engine = engine
        if self.engine not in ["podman", "docker"]:
            raise ValueError(f"Unsupported container engine: {self.engine}")
        self.base_work_dir = remote_access.prepare()

    def get_env(self):
        env_ = dict(HOME=self.base_work_dir)
        if config.project.get_config("prepare.podman.machine.enabled", print=False):
            env_ |= config.project.get_config("prepare.podman.machine.env", print=False)

        return env_

    def get_command(self):
        cmd = self.engine
        podman_env = self.get_env

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


class podman_machine:
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

    def configure_and_start(self, force_restart=False):
        cmd = f"podman machine init --name {self.machine_name} --rootful"
        if force_restart:
            cmd += " --force"

        cmd = f"{self.get_cmd_env()} {cmd}"
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir,
                                                f"{self.get_cmd_env()} podman machine start {self.machine_name}")

    def start(self):
        cmd = f"{self.get_cmd_env()} podman machine start {self.machine_name}"
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)

    def stop(self):
        cmd = f"{self.get_cmd_env()} podman machine stop {self.machine_name}"
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)

    def rm(self):
        cmd = f"{self.get_cmd_env()} podman machine rm {self.machine_name} --force"
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)

    def reset(self):
        cmd = f"{self.get_cmd_env()} podman machine reset {self.machine_name} --force"
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)

    def is_running(self):
        machine_state = self.inspect()
        if not machine_state:
            return None

        return machine_state[0]["State"] != "stopped"

    def inspect(self):
        cmd = f"{self.get_cmd_env()} podman machine inspect {self.machine_name}"
        inspect_cmd = remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd, capture_stdout=True, check=False)
        if inspect_cmd.returncode != 0:
            if "VM does not exist" in inspect_cmd.stdout:
                logging.info("podman_machine: inspect: VM does not exist")
            else:
                logging.error(f"podman_machine: inspect: unhandled status: {inspect_cmd.stdout.strip()}")
            return None

        return json.loads(inspect_cmd.stdout)
