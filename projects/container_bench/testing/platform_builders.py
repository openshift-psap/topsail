from abc import ABC, abstractmethod
from config_manager import ConfigManager
import shlex


class PlatformCommandBuilder(ABC):
    @abstractmethod
    def build_env_command(self, env_dict):
        pass

    @abstractmethod
    def build_service_start_script(self, service_name, start_command, binary_path):
        pass

    @abstractmethod
    def build_chdir_command(self, chdir):
        pass

    @abstractmethod
    def build_rm_command(self, file_path, recursive=False):
        pass

    @abstractmethod
    def build_mkdir_command(self, path):
        pass

    @abstractmethod
    def build_exists_command(self, path):
        pass

    @abstractmethod
    def get_shell_command(self):
        pass

    @abstractmethod
    def build_entrypoint_script(self, env_cmd, chdir_cmd, cmd, verbose):
        pass

    @abstractmethod
    def check_exists_result(self, ret):
        pass


def escape_powershell_single_quote(value):
    return str(value).replace("'", "''")


class WindowsCommandBuilder(PlatformCommandBuilder):
    def build_env_command(self, env_dict):
        if not env_dict:
            return ""

        env_commands = []
        for k, v in env_dict.items():
            if v is None or v == "":
                continue
            env_commands.append(f"$env:{escape_powershell_single_quote(k)}='{escape_powershell_single_quote(v)}'")
        return "; ".join(env_commands) + ";"

    def build_service_start_script(self, service_name, start_command, binary_path):
        return f"""
$scriptContent = @"
& {start_command} *>&1 | Out-File -FilePath "`$env:USERPROFILE\\{service_name}_script_log.txt"
"@

Set-Content -Path "$env:USERPROFILE\\start_{service_name}.ps1" -Value $scriptContent
$command = "powershell.exe -ExecutionPolicy Bypass -File `"$env:USERPROFILE\\start_{service_name}.ps1`""

$result = Invoke-WmiMethod -Class Win32_Process -Name Create -ArgumentList $command

# Wait for {service_name} to be fully ready
Write-Output "Waiting for {service_name} to boot..."
$timeout = 120  # 2 minutes timeout
$elapsed = 0
$interval = 5

while ($elapsed -lt $timeout) {{
    try {{
        & "{binary_path}" info *>$null
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

    def build_chdir_command(self, chdir):
        if chdir is None:
            return "Set-Location $env:USERPROFILE"
        return f"Set-Location '{escape_powershell_single_quote(chdir)}'"

    def build_rm_command(self, file_path, recursive=False):
        flags = "-Force -ErrorAction SilentlyContinue"
        if recursive:
            flags += " -Recurse"
        return f"Remove-Item '{escape_powershell_single_quote(str(file_path))}' {flags}"

    def build_mkdir_command(self, path):
        return f"New-Item -ItemType Directory -Path '{escape_powershell_single_quote(str(path))}' -Force"

    def build_exists_command(self, path):
        return f"Test-Path '{escape_powershell_single_quote(str(path))}'"

    def get_shell_command(self):
        return "powershell.exe -Command -"

    def build_entrypoint_script(self, env_cmd, chdir_cmd, cmd, verbose):
        env_section = f"{env_cmd}\n" if env_cmd else ""
        script = f"""
$ErrorActionPreference = "Stop"

{env_section}{chdir_cmd}

{cmd}
    """
        if verbose:
            script = f"$VerbosePreference = 'Continue'\n{script}"
        return script

    def check_exists_result(self, ret):
        return ret.stdout and ret.stdout.strip().lower() == "true"


class UnixCommandBuilder(PlatformCommandBuilder):
    def build_env_command(self, env_dict):
        if not env_dict:
            return ""

        env_values = " ".join(f"{k}={shlex.quote(str(v))}" for k, v in env_dict.items() if v is not None and v != "")
        return f"export {env_values}\n"

    def build_service_start_script(self, service_name, start_command, binary_path) -> str:
        return start_command

    def build_chdir_command(self, chdir):
        if chdir is None:
            return "cd $HOME"
        return f"cd '{shlex.quote(str(chdir))}'"

    def build_rm_command(self, file_path, recursive=False):
        flag = "-rf" if recursive else "-f"
        return f"rm {flag} {shlex.quote(str(file_path))}"

    def build_mkdir_command(self, path):
        return f"mkdir -p {shlex.quote(str(path))}"

    def build_exists_command(self, path):
        return f"test -e {shlex.quote(str(path))}"

    def get_shell_command(self):
        return "bash"

    def build_entrypoint_script(self, env_cmd, chdir_cmd, cmd, verbose):
        script = f"""
set -o pipefail
set -o errexit
set -o nounset
set -o errtrace

{env_cmd}

{chdir_cmd}

{cmd}
    """
        if verbose:
            script = f"set -x\n{script}"
        return script

    def check_exists_result(self, ret):
        return ret.returncode == 0


class PlatformFactory:
    @staticmethod
    def create_command_builder():
        if ConfigManager.is_windows():
            return WindowsCommandBuilder()
        else:
            return UnixCommandBuilder()


def build_env_command(env_dict):
    builder = PlatformFactory.create_command_builder()
    return builder.build_env_command(env_dict)


def build_service_start_script(service_name, start_command, binary_path):
    builder = PlatformFactory.create_command_builder()
    return builder.build_service_start_script(service_name, start_command, binary_path)
