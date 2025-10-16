import os
import pathlib
import logging
import utils
import yaml
import shlex

from projects.core.library import config, run
from constants import CONTAINER_BENCH_SECRET_PATH
from config_manager import ConfigManager


def prepare():
    base_work_dir = pathlib.Path(config.project.get_config("remote_host.base_work_dir", handled_secretly=True))

    if config.project.get_config("remote_host.run_locally", print=False):
        logging.info("Running locally, nothing to prepare.")
        return base_work_dir

    if os.environ.get("TOPSAIL_REMOTE_HOSTNAME"):
        # already prepared
        logging.debug("Already prepared, no need to prepare again")
        return base_work_dir

    #

    remote_hostname = config.project.get_config("remote_host.hostname", handled_secretly=True)
    remote_username = config.project.get_config("remote_host.username", handled_secretly=True)

    os.environ["TOPSAIL_REMOTE_HOSTNAME"] = remote_hostname
    os.environ["TOPSAIL_REMOTE_USERNAME"] = remote_username
    os.environ["TOPSAIL_REMOTE_OS"] = ConfigManager.get_system_type().value

    #

    extra_vars_fd_path, extra_vars_file = utils.get_tmp_fd()

    os.environ["TOPSAIL_ANSIBLE_PLAYBOOK_EXTRA_VARS"] = extra_vars_fd_path

    #

    extra_env_fd_path, extra_env_file = utils.get_tmp_fd()
    env = config.project.get_config("remote_host.env") or {}

    for k, v in env.copy().items():
        if not v:
            del env[k]
            continue

        if not v.startswith("*$@"):
            continue
        env[k] = config.project.get_config(f"remote_host.env.{k}", handled_secretly=True).strip()

    if config.project.get_config("remote_host.home_is_base_work_dir"):
        env["HOME"] = str(base_work_dir)

    yaml.dump(env, extra_env_file)
    extra_env_file.flush()

    os.environ["TOPSAIL_ANSIBLE_PLAYBOOK_EXTRA_ENV"] = extra_env_fd_path

    #

    private_key_path = CONTAINER_BENCH_SECRET_PATH / config.project.get_config("remote_host.private_key_filename")

    remote_hostport = config.project.get_config("remote_host.port")

    ssh_flags = config.project.get_config("remote_host.ssh_flags")

    extra_vars_yaml_content = f"""
ansible_port: {remote_hostport}
ansible_ssh_private_key_file: {private_key_path}
ansible_ssh_user: {remote_username}
ansible_ssh_common_args: "{' '.join(ssh_flags)}"
"""

    print(extra_vars_yaml_content, file=extra_vars_file)
    extra_vars_file.flush()

    #

    return base_work_dir


def run_with_ansible_ssh_conf_windows(
        base_work_dir, cmd,
        extra_env=None,
        check=True,
        capture_stdout=False,
        capture_stderr=False,
        chdir=None,
        print_cmd=False,
):
    if extra_env is None:
        extra_env = {}

    run_kwargs = dict(
        log_command=False,
        check=check,
        capture_stdout=capture_stdout,
        capture_stderr=capture_stderr,
    )

    if config.project.get_config("remote_host.run_locally", print=False):
        logging.info(f"Running on the local Windows host: {cmd}")
        return run.run(cmd, **run_kwargs)

    with open(os.environ["TOPSAIL_ANSIBLE_PLAYBOOK_EXTRA_VARS"]) as f:
        ansible_ssh_config = yaml.safe_load(f)

    ssh_flags = ansible_ssh_config["ansible_ssh_common_args"]
    host = os.environ["TOPSAIL_REMOTE_HOSTNAME"]
    port = ansible_ssh_config["ansible_port"]
    user = ansible_ssh_config["ansible_ssh_user"]
    private_key_path = ansible_ssh_config["ansible_ssh_private_key_file"]

    with open(os.environ["TOPSAIL_ANSIBLE_PLAYBOOK_EXTRA_ENV"]) as f:
        ansible_extra_env = yaml.safe_load(f)

    def escape_powershell_single_quote(value):
        """Escape single quotes in PowerShell by replacing ' with ''"""
        return str(value).replace("'", "''")

    env_vars = ansible_extra_env | extra_env
    if env_vars:
        env_cmd = "\n".join(
            f"$env:{escape_powershell_single_quote(k)}='{escape_powershell_single_quote(v)}'"
            for k, v in env_vars.items()
        )
    else:
        env_cmd = ""

    chdir_cmd = f"Set-Location '{escape_powershell_single_quote(chdir)}'" if chdir else "Set-Location $env:USERPROFILE"

    tmp_file_path, tmp_file = utils.get_tmp_fd()

    env_section = f"{env_cmd}\n" if env_cmd else ""

    entrypoint_script = f"""
$ErrorActionPreference = "Stop"

{env_section}{chdir_cmd}

{cmd}
    """

    if config.project.get_config("remote_host.verbose_ssh_commands", print=False):
        entrypoint_script = f"$VerbosePreference = 'Continue'\n{entrypoint_script}"

    logging.info(f"Running on the remote Windows host: {chdir_cmd}; {cmd}")

    with open(tmp_file_path, "w") as f:
        print(entrypoint_script, file=f)
    if print_cmd:
        print(entrypoint_script)

    proc = run.run(f"ssh {ssh_flags} -i {private_key_path} {user}@{host} -p {port} -- "
                   "powershell.exe -Command -",
                   **run_kwargs, stdin_file=tmp_file)

    return proc


def run_with_ansible_ssh_conf_unix(
        base_work_dir, cmd,
        extra_env=None,
        check=True,
        capture_stdout=False,
        capture_stderr=False,
        chdir=None,
        print_cmd=False,
):
    """Linux/Unix-specific SSH execution function using bash."""
    if extra_env is None:
        extra_env = {}

    run_kwargs = dict(
        log_command=False,
        check=check,
        capture_stdout=capture_stdout,
        capture_stderr=capture_stderr,
    )

    if config.project.get_config("remote_host.run_locally", print=False):
        logging.info(f"Running on the local Unix host: {cmd}")
        return run.run(cmd, **run_kwargs)

    with open(os.environ["TOPSAIL_ANSIBLE_PLAYBOOK_EXTRA_VARS"]) as f:
        ansible_ssh_config = yaml.safe_load(f)

    ssh_flags = ansible_ssh_config["ansible_ssh_common_args"]
    host = os.environ["TOPSAIL_REMOTE_HOSTNAME"]
    port = ansible_ssh_config["ansible_port"]
    user = ansible_ssh_config["ansible_ssh_user"]
    private_key_path = ansible_ssh_config["ansible_ssh_private_key_file"]

    with open(os.environ["TOPSAIL_ANSIBLE_PLAYBOOK_EXTRA_ENV"]) as f:
        ansible_extra_env = yaml.safe_load(f)

    export_cmd = "\n".join(f"export {k}='{v}'" for k, v in (ansible_extra_env | extra_env).items())

    chdir_cmd = f"cd '{chdir}'" if chdir else "cd $HOME"

    tmp_file_path, tmp_file = utils.get_tmp_fd()

    entrypoint_script = f"""
set -o pipefail
set -o errexit
set -o nounset
set -o errtrace

{export_cmd}

{chdir_cmd}

exec {cmd}
    """

    if config.project.get_config("remote_host.verbose_ssh_commands", print=False):
        entrypoint_script = f"set -x\n{entrypoint_script}"

    logging.info(f"Running on the remote Unix host: {chdir_cmd}; {cmd}")

    with open(tmp_file_path, "w") as f:
        print(entrypoint_script, file=f)
    if print_cmd:
        print(entrypoint_script)

    proc = run.run(f"ssh {ssh_flags} -i {private_key_path} {user}@{host} -p {port} -- "
                   "bash",
                   **run_kwargs, stdin_file=tmp_file)

    return proc


def run_with_ansible_ssh_conf(
        base_work_dir, cmd,
        extra_env=None,
        check=True,
        capture_stdout=False,
        capture_stderr=False,
        chdir=None,
        print_cmd=False,
):
    if ConfigManager.is_windows():
        return run_with_ansible_ssh_conf_windows(
            base_work_dir, cmd,
            extra_env=extra_env,
            check=check,
            capture_stdout=capture_stdout,
            capture_stderr=capture_stderr,
            chdir=chdir,
            print_cmd=print_cmd,
        )
    else:
        return run_with_ansible_ssh_conf_unix(
            base_work_dir, cmd,
            extra_env=extra_env,
            check=check,
            capture_stdout=capture_stdout,
            capture_stderr=capture_stderr,
            chdir=chdir,
            print_cmd=print_cmd,
        )


def exists_windows(path):
    if config.project.get_config("remote_host.run_locally", print=False):
        return path.exists()

    base_work_dir = prepare()

    ret = run_with_ansible_ssh_conf_windows(
        base_work_dir,
        f"Test-Path '{path}'",
        capture_stdout=True,
        check=False,
    )

    # PowerShell Test-Path returns "True" or "False" as text
    return ret.stdout and ret.stdout.strip().lower() == "true"


def exists_unix(path):
    if config.project.get_config("remote_host.run_locally", print=False):
        return path.exists()

    base_work_dir = prepare()

    ret = run_with_ansible_ssh_conf_unix(
        base_work_dir,
        f"test -e {shlex.quote(str(path))}",
        capture_stdout=True,
        check=False,
    )

    return ret.returncode == 0


def exists(path):
    if ConfigManager.is_windows():
        return exists_windows(path)
    else:
        return exists_unix(path)
