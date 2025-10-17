import remote_access
import json
import logging

from config_manager import ConfigManager
from platform_builders import build_env_command, build_service_start_script


def get_podman_binary(base_work_dir):
    podman_config = ConfigManager.get_podman_config()
    custom_binary_config = ConfigManager.get_custom_binary_config()

    if podman_config['repo_enabled']:
        version = podman_config['repo_version']
        podman_bin = base_work_dir / f"podman-{version}" / "usr" / "bin" / "podman"
        if ConfigManager.is_linux():
            podman_bin = base_work_dir / f"podman-{version}" / "bin" / "podman"
    else:
        podman_bin = ConfigManager.get_binary_path("podman")

    if custom_binary_config['enabled']:
        podman_file = custom_binary_config['client_file']
        if ConfigManager.is_linux():
            podman_file = custom_binary_config['server_file']
        podman_bin = base_work_dir / "podman-custom" / podman_file
        if not remote_access.exists(podman_bin):
            podman_bin = ConfigManager.get_binary_path("podman")

    return podman_bin


class ContainerEngine:
    def __init__(self, engine):
        self.engine = engine
        if self.engine not in ["podman", "docker"]:
            raise ValueError(f"Unsupported container engine: {self.engine}")
        self.base_work_dir = remote_access.prepare()
        self.podman_config = ConfigManager.get_podman_config()

        if self.engine == "podman":
            self.engine_binary = get_podman_binary(self.base_work_dir)
        elif self.engine == "docker":
            self.engine_binary = ConfigManager.get_binary_path("docker")

    def get_env(self):
        env_ = dict(HOME=self.base_work_dir)
        if self.engine == "docker":
            return env_

        if self.podman_config['machine_enabled']:
            env_ |= self.podman_config['machine_env'] or {}

        return env_

    def get_command(self):
        cmd = self.engine_binary
        if self.engine == "docker":
            return cmd

        env_cmd = build_env_command(self.get_env())

        is_linux = ConfigManager.is_linux()

        if self.podman_config['machine_enabled'] and not is_linux:
            machine_name = self.podman_config['machine_name']
            cmd = f"{cmd} --connection '{machine_name}'"

        if is_linux:
            if self.podman_config['linux_rootful']:
                cmd = f"sudo -E {cmd}"
            if runtime := self.podman_config['linux_runtime']:
                cmd = f"{cmd} --runtime {runtime}"

        cmd = f"{env_cmd} {cmd}"

        return cmd

    def is_rootful(self):
        if ConfigManager.is_linux():
            return self.podman_config['linux_rootful']
        return False  # Rootfull podman is running in a VM on non-Linux hosts

    def additional_args(self):
        additional_args = ""
        if self.engine == "docker":
            return additional_args
        if ConfigManager.is_linux():
            if runtime := self.podman_config['linux_runtime']:
                additional_args = f"{additional_args} --runtime {runtime}"
        return additional_args

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
        self.base_work_dir = remote_access.prepare()
        self.podman_config = ConfigManager.get_podman_config()
        self.machine_name = self.podman_config['machine_name']

    def get_env(self):
        env_ = dict(HOME=self.base_work_dir)
        if self.podman_config['machine_enabled']:
            env_ |= self.podman_config['machine_env'] or {}

        return env_

    def get_cmd_env(self):
        env_dict = self.get_env()
        return build_env_command(env_dict)

    def configure_and_start(self, force_restart=True, configure=False):
        machine_state = self.inspect()
        if not machine_state:
            self.init()
            machine_state = self.inspect()
        was_stopped = machine_state[0]["State"] == "stopped"

        machine_config = ConfigManager.get_podman_machine_config()

        if force_restart and not was_stopped:
            if machine_config['force_configuration']:
                self.stop()
                was_stopped = True

        if not was_stopped:
            logging.info("podman machine already running. Skipping the configuration part.")
            return

        if machine_config['set_default']:
            name = machine_config['name']
            rootless = ""
            if machine_config['configuration_rootful']:
                rootless = "-root"
            remote_access.run_with_ansible_ssh_conf(
                self.base_work_dir,
                f"{self.get_cmd_env()} {get_podman_binary(self.base_work_dir)} system connection default"
                f" {name}{rootless}"
            )

        if configure:
            self.configure()

        self.start()

        machine_state = self.inspect()
        if not machine_state:
            msg = "Podman machine failed to start :/"
            logging.error(msg)
            raise RuntimeError(msg)

        custom_binary_config = ConfigManager.get_custom_binary_config()
        if custom_binary_config['enabled']:
            podman_file = custom_binary_config['server_file']
            podman_bin = self.base_work_dir / "podman-custom" / podman_file
            self.cp(podman_bin, "~/podman")
            ret = self.ssh("chmod +x ./podman")
            if ret.returncode != 0:
                raise RuntimeError("Failed to make custom podman server binary executable")
            ret = self.ssh("./podman system service -t 0 >/dev/null 2>&1 &")
            if ret.returncode != 0:
                raise RuntimeError("Failed to start custom podman server")

    def configure(self):
        name = self.podman_config['machine_name']
        machine_config = ConfigManager.get_podman_machine_config()
        configuration = machine_config['configuration']
        is_wsl = machine_config['env_containers_machine_provider'] == "wsl"
        # Changing CPUs, Memory not supported for WSL machines
        if ConfigManager.is_windows() and is_wsl:
            if "cpus" in configuration:
                del configuration["cpus"]
            if "memory" in configuration:
                del configuration["memory"]

        config_str = " ".join(f"--{k}={v}" for k, v in configuration.items())

        remote_access.run_with_ansible_ssh_conf(
            self.base_work_dir,
            f"{self.get_cmd_env()} {get_podman_binary(self.base_work_dir)} machine set {config_str} {name}"
        )

    def init(self):
        cmd = f"{get_podman_binary(self.base_work_dir)} machine init {self.machine_name}"
        cmd = f"{self.get_cmd_env()} {cmd}"
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)

    def start(self):
        start_command = f"{get_podman_binary(self.base_work_dir)} machine start {self.machine_name}"
        cmd = f"{self.get_cmd_env()} {start_command}"

        if ConfigManager.is_windows():
            # Use platform-specific service start script for Windows
            cmd = build_service_start_script(
                service_name="podman",
                start_command=start_command,
                binary_path=str(get_podman_binary(self.base_work_dir))
            )

        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)

    def stop(self):
        cmd = f"{self.get_cmd_env()} {get_podman_binary(self.base_work_dir)} machine stop {self.machine_name}"
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)

    def rm(self):
        cmd = f"{self.get_cmd_env()} {get_podman_binary(self.base_work_dir)} machine rm {self.machine_name} --force"
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd, check=False)
        if ConfigManager.is_windows():
            cmd = "Remove-Item $env:USERPROFILE\\podman_script_log.txt -Force -ErrorAction SilentlyContinue"
            remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd, check=False)

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
        inspect_cmd = remote_access.run_with_ansible_ssh_conf(
            self.base_work_dir, cmd,
            capture_stderr=True, capture_stdout=True, check=False
        )
        if inspect_cmd.returncode != 0:
            if "VM does not exist" in inspect_cmd.stderr:
                logging.info("podman_machine: inspect: VM does not exist")
            else:
                logging.error(f"podman_machine: inspect: unhandled status: {inspect_cmd.stderr.strip()}")
            return None

        return json.loads(inspect_cmd.stdout)

    def cp(self, source, dest):
        cmd = f"{get_podman_binary(self.base_work_dir)} machine cp {source} {self.machine_name}:{dest}"
        cmd = f"{self.get_cmd_env()} {cmd}"
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)

    def ssh(self, command):
        cmd = f"{get_podman_binary(self.base_work_dir)} machine ssh {self.machine_name} '{command}'"
        cmd = f"{self.get_cmd_env()} {cmd}"
        return remote_access.run_with_ansible_ssh_conf(
            self.base_work_dir,
            cmd,
            check=False,
            capture_stdout=True,
            capture_stderr=True,
        )


class DockerDesktopMachine:
    # Requires Docker Desktop to be installed and running on the remote Mac.
    # Aka testing user must be logged in to the system. And home_is_base_work_dir: false
    def __init__(self):
        self.base_work_dir = remote_access.prepare()
        # cmd = f"ln -Fs {self.base_work_dir / '../.docker'} {self.base_work_dir / '.docker'}"
        # remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)

    def start(self):
        start_command = "docker desktop start"
        cmd = start_command

        if ConfigManager.is_windows():
            # Use platform-specific service start script for Windows
            cmd = build_service_start_script(
                service_name="docker",
                start_command=start_command,
                binary_path="docker"
            )

        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)

    def stop(self):
        cmd = "docker desktop stop"
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)
        if ConfigManager.is_windows():
            cmd = "Remove-Item $env:USERPROFILE\\docker_script_log.txt -Force -ErrorAction SilentlyContinue"
            remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd, check=False)

    def is_running(self):
        cmd = "docker desktop status"
        result = remote_access.run_with_ansible_ssh_conf(
            self.base_work_dir, cmd,
            capture_stdout=True, capture_stderr=True, check=False
        )
        if "You can start Docker Desktop" in result.stderr.strip():
            return False

        if result.returncode != 0:
            logging.error(
                f"Docker Desktop status check failed:\n"
                f"STDOUT: {result.stdout.strip()}\nSTDERR: {result.stderr.strip()}"
            )
            return None

        return "running" in result.stdout.lower()
