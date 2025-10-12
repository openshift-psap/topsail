import remote_access
import json
import logging

from projects.core.library import config


def build_env_command_windows(env_dict):
    """Build PowerShell environment variable setting command for Windows."""
    if not env_dict:
        return ""

    env_commands = []
    for k, v in env_dict.items():
        env_commands.append(f"$env:{k}='{v}'")

    return "; ".join(env_commands) + ";"


def build_env_command_unix(env_dict):
    """Build Unix env command for setting environment variables."""
    if not env_dict:
        return ""

    env_values = " ".join(f"'{k}={v}'" for k, v in env_dict.items())
    return f"env {env_values}"


def build_env_command(env_dict):
    """Build environment command based on target system type."""
    is_windows = config.project.get_config("remote_host.system", print=False) == "windows"

    if is_windows:
        return build_env_command_windows(env_dict)
    else:
        return build_env_command_unix(env_dict)


def build_windows_start_script(service_name, start_command, binary_path):
    """Build PowerShell script for starting services on Windows with wait logic."""
    return f"""
$scriptContent = @"
& {start_command} *>&1 | Out-File -FilePath "`$env:USERPROFILE\\{service_name}_script_log.txt"
"@

Set-Content -Path "$env:USERPROFILE\\start_{service_name}.ps1" -Value $scriptContent
$command = "powershell.exe -ExecutionPolicy Bypass -File `"$env:USERPROFILE\\start_{service_name}.ps1`""

$result = Invoke-WmiMethod -Class Win32_Process -Name Create -ArgumentList $command

# Wait for {service_name} to be fully ready using while loop
Write-Output "Waiting for {service_name} to boot..."
$timeout = 120  # 2 minutes timeout
$elapsed = 0
$interval = 5

while ($elapsed -lt $timeout) {{
    try {{
        & {binary_path} info *>$null
        if ($LASTEXITCODE -eq 0) {{
            Write-Output "{service_name.capitalize()} is ready after $elapsed seconds"
            break
        }}
    }} catch {{
        # Continue waiting
    }}

    Write-Output "Still waiting... ($elapsed/$timeout seconds)"
    Start-Sleep -Seconds $interval
    $elapsed += $interval
}}

if ($elapsed -ge $timeout) {{
    Write-Output "Warning: Timeout waiting for {service_name} to be ready"
    type $env:USERPROFILE\\{service_name}_script_log.txt
}}

Remove-Item "$env:USERPROFILE\\start_{service_name}.ps1" -Force -ErrorAction SilentlyContinue
"""


def get_podman_binary(base_work_dir):
    if config.project.get_config("prepare.podman.repo.enabled", print=False):
        version = config.project.get_config("prepare.podman.repo.version", print=False)
        podman_bin = base_work_dir / f"podman-{version}" / "usr" / "bin" / "podman"
        if config.project.get_config("remote_host.system", print=False) == "linux":
            podman_bin = base_work_dir / f"podman-{version}" / "bin" / "podman"
    else:
        podman_bin = config.project.get_config("remote_host.podman_bin", print=False) or "podman"

    if config.project.get_config("prepare.podman.custom_binary.enabled", print=False):
        podman_file = config.project.get_config("prepare.podman.custom_binary.client_file", print=False)
        if config.project.get_config("remote_host.system", print=False) == "linux":
            podman_file = config.project.get_config("prepare.podman.custom_binary.server_file", print=False)
        podman_bin = base_work_dir / "podman-custom" / podman_file
        if not remote_access.exists(podman_bin):
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

        env_cmd = build_env_command(self.get_env())

        is_linux = config.project.get_config("remote_host.system", print=False) == "linux"

        if config.project.get_config("prepare.podman.machine.enabled", print=False) and not is_linux:
            machine_name = config.project.get_config("prepare.podman.machine.name", print=False)
            cmd = f"{cmd} --connection '{machine_name}'"

        if is_linux:
            if config.project.get_config("prepare.podman.linux.rootful", print=False):
                cmd = f"sudo {cmd}"
            if runtime := config.project.get_config("prepare.podman.linux.runtime", print=False):
                cmd = f"{cmd} --runtime {runtime}"

        cmd = f"{env_cmd} {cmd}"

        return cmd

    def is_rootful(self):
        if config.project.get_config("remote_host.system", print=False) == "linux":
            return config.project.get_config("prepare.podman.linux.rootful", print=False)
        return config.project.get_config("prepare.podman.machine.rootful", print=False)

    def additional_args(self):
        additional_args = ""
        if self.engine == "docker":
            return additional_args
        if config.project.get_config("remote_host.system", print=False) == "linux":
            if runtime := config.project.get_config("prepare.podman.linux.runtime", print=False):
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
        self.machine_name = config.project.get_config("prepare.podman.machine.name", print=False)
        self.base_work_dir = remote_access.prepare()

    def get_env(self):
        env_ = dict(HOME=self.base_work_dir)
        if config.project.get_config("prepare.podman.machine.enabled", print=False):
            env_ |= config.project.get_config("prepare.podman.machine.env", print=False)

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

        if force_restart and not was_stopped:
            if config.project.get_config("prepare.podman.machine.force_configuration"):
                self.stop()
                was_stopped = True

        if not was_stopped:
            logging.info("podman machine already running. Skipping the configuration part.")
            return

        if config.project.get_config("prepare.podman.machine.set_default"):
            name = config.project.get_config("prepare.podman.machine.name", print=False)
            rootless = ""
            if config.project.get_config("prepare.podman.machine.configuration.rootful", print=False):
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

        if config.project.get_config("prepare.podman.custom_binary.enabled", print=False):
            podman_file = config.project.get_config("prepare.podman.custom_binary.server_file", print=False)
            podman_bin = self.base_work_dir / "podman-custom" / podman_file
            self.cp(podman_bin, "~/podman")
            ret = self.ssh("chmod +x ./podman")
            if ret.returncode != 0:
                raise RuntimeError("Failed to make custom podman server binary executable")
            ret = self.ssh("./podman system service -t 0 >/dev/null 2>&1 &")
            if ret.returncode != 0:
                raise RuntimeError("Failed to start custom podman server")

    def configure(self):
        name = config.project.get_config("prepare.podman.machine.name", print=False)
        configuration = config.project.get_config("prepare.podman.machine.configuration")
        is_windows = config.project.get_config("remote_host.system", print=False) == "windows"
        is_wsl = config.project.get_config("prepare.podman.machine.env.CONTAINERS_MACHINE_PROVIDER") == "wsl"
        # Changing CPUs, Memory not supported for WSL machines
        if is_windows and is_wsl:
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
        cmd = f"{self.get_cmd_env()} {get_podman_binary(self.base_work_dir)} machine start {self.machine_name}"
        is_windows = config.project.get_config("remote_host.system", print=False) == "windows"
        if is_windows:
            # Environment variables must be set permanently using setx, because machine is started in a new shell.
            # To survive the exit of ssh session.
            # -------------
            cmd = build_windows_start_script(
                service_name="podman",
                start_command=f"{get_podman_binary(self.base_work_dir)} machine start {self.machine_name}",
                binary_path=get_podman_binary(self.base_work_dir)
            )
            # -------------
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)

    def stop(self):
        cmd = f"{self.get_cmd_env()} {get_podman_binary(self.base_work_dir)} machine stop {self.machine_name}"
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)

    def rm(self):
        cmd = f"{self.get_cmd_env()} {get_podman_binary(self.base_work_dir)} machine rm {self.machine_name} --force"
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd, check=False)
        if config.project.get_config("remote_host.system", print=False) == "windows":
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
        cmd = "docker desktop start"
        is_windows = config.project.get_config("remote_host.system", print=False) == "windows"
        if is_windows:
            # Environment variables must be set permanently using setx, because machine is started in a new shell.
            # To survive the exit of ssh session.
            # -------------
            cmd = build_windows_start_script(
                service_name="docker",
                start_command="docker desktop start",
                binary_path="docker"
            )
            # -------------
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)

    def stop(self):
        cmd = "docker desktop stop"
        remote_access.run_with_ansible_ssh_conf(self.base_work_dir, cmd)
        if config.project.get_config("remote_host.system", print=False) == "windows":
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
