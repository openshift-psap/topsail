import os
import pathlib
import logging
import yaml

from projects.core.library import env, config, run, configure_logging, export
import utils

def prepare():
    from prepare_mac_ai import CRC_MAC_AI_SECRET_PATH
    base_work_dir = pathlib.Path(config.project.get_config("remote_host.base_work_dir", handled_secretly=True))

    #

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

        if not v.startswith("*$@"): continue
        env[k] = config.project.get_config(f"remote_host.env.{k}", handled_secretly=True).strip()

    yaml.dump(env, extra_env_file)
    extra_env_file.flush()

    os.environ["TOPSAIL_ANSIBLE_PLAYBOOK_EXTRA_ENV"] = extra_env_fd_path

    #

    private_key_path = CRC_MAC_AI_SECRET_PATH / config.project.get_config("remote_host.private_key_filename")

    remote_hostport = config.project.get_config("remote_host.port")

    ssh_flags = config.project.get_config("remote_host.ssh_flags")

    extra_vars_yaml_content = f"""
ansible_port: {remote_hostport}
ansible_ssh_private_key_file: {private_key_path}
ansible_ssh_user: {remote_username}
ansible_ssh_common_args: "{' '.join(ssh_flags)}"
"""
    print(extra_vars_yaml_content)
    print(extra_vars_yaml_content, file=extra_vars_file)
    extra_vars_file.flush()

    #

    return base_work_dir


def run_with_ansible_ssh_conf(
        base_work_dir, cmd,
        extra_env={},
        check=True,
        capture_stdout=False,
        capture_stderr=False,
        chdir=None,
        print_cmd=False,
):
    run_kwargs = dict(
        log_command=False,
        check=check,
        capture_stdout=capture_stdout,
        capture_stderr=capture_stderr,
    )

    if config.project.get_config("remote_host.run_locally", print=False):
        logging.info(f"Running on the local host: {cmd}")

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

    export_cmd = "\n".join(f"export {k}='{v}'" for k, v in (ansible_extra_env|extra_env).items())

    chdir_cmd = f"cd '{chdir}'" if chdir else "cd $HOME # no explicit chdir"

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

    logging.info(f"Running on the remote host: {chdir_cmd}; {cmd}")

    with open(tmp_file_path, "w") as f:
        print(entrypoint_script, file=f)
    if print_cmd:
        print(entrypoint_script)

    return run.run(f"ssh {ssh_flags} -i {private_key_path} {user}@{host} -p {port} -- "
                   "bash",
                   **run_kwargs, stdin_file=tmp_file)

def exists(path):
    if config.project.get_config("remote_host.run_locally", print=False):
        return path.exists()
    base_work_dir = prepare()
    test_flag = '-e'

    ret = run_with_ansible_ssh_conf(
        base_work_dir,
        f"test {test_flag} {path}",
        capture_stdout=True,
        check=False,
    )

    return ret.returncode == 0
