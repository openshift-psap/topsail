from abc import ABC, abstractmethod
from config_manager import ConfigManager


class PlatformCommandBuilder(ABC):
    @abstractmethod
    def build_env_command(self, env_dict):
        pass

    @abstractmethod
    def build_service_start_script(self, service_name, start_command, binary_path):
        pass


class WindowsCommandBuilder(PlatformCommandBuilder):
    def build_env_command(self, env_dict):
        if not env_dict:
            return ""

        env_commands = []
        for k, v in env_dict.items():
            env_commands.append(f"$env:{k}='{v}'")

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


class UnixCommandBuilder(PlatformCommandBuilder):
    def build_env_command(self, env_dict):
        if not env_dict:
            return ""

        env_values = " ".join(f"'{k}={v}'" for k, v in env_dict.items())
        return f"env {env_values}"

    def build_service_start_script(self, service_name, start_command, binary_path) -> str:
        return start_command


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
