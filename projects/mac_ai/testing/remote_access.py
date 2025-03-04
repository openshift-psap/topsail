import os
import pathlib
import logging
import yaml

from projects.core.library import env, config, run, configure_logging, export
import utils

def prepare():
    from prepare_mac_ai import CRC_MAC_AI_SECRET_PATH
    base_work_dir = config.project.get_config("remote_host.base_work_dir", print=False)
    if base_work_dir.startswith("@"):
        with open(CRC_MAC_AI_SECRET_PATH / config.project.get_config(base_work_dir[1:], print=False)) as f:
            base_work_dir = pathlib.Path(f.read().strip())

    base_work_dir = pathlib.Path(base_work_dir)

    #

    if config.project.get_config("remote_host.run_locally", print=False):
        logging.info("Running locally, nothing to prepare.")
        return base_work_dir


    if os.environ.get("TOPSAIL_REMOTE_HOSTNAME"):
        # already prepared
        logging.debug("Already prepared, no need to prepare again")
        return base_work_dir

    #

    remote_hostname = config.project.get_config("remote_host.hostname")
    if remote_hostname.startswith("@"):
        with open(CRC_MAC_AI_SECRET_PATH / config.project.get_config(remote_hostname[1:])) as f:
            remote_hostname = f.read().strip()

    remote_username = config.project.get_config("remote_host.username")
    if remote_username.startswith("@"):
        with open(CRC_MAC_AI_SECRET_PATH / config.project.get_config(remote_username[1:])) as f:
            remote_username = f.read().strip()


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

        if not v.startswith("@"): continue
        cfg_key = v[1:]
        if cfg_key == "secrets.base_work_dir":
            env[k] = str(base_work_dir)
        else:
            env[k] = config.project.get_config()

    yaml.dump(env, extra_env_file)
    extra_env_file.flush()

    os.environ["TOPSAIL_ANSIBLE_PLAYBOOK_EXTRA_ENV"] = extra_env_fd_path

    #
    private_key_path = config.project.get_config("remote_host.private_key_path")
    if private_key_path.startswith("@"):
        private_key_path = CRC_MAC_AI_SECRET_PATH / config.project.get_config(private_key_path[1:])

    remote_hostport = config.project.get_config("remote_host.port")
    if isinstance(remote_hostport, str) and remote_hostport.startswith("@"):
        with open(CRC_MAC_AI_SECRET_PATH / config.project.get_config(remote_hostport[1:])) as f:
            remote_hostport = int(f.read().strip())

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

    logging.info(f"Running on the jump host: {cmd}")

    base_env = dict(HOME=base_work_dir)

    env_values = " ".join(f"'{k}={v}'" for k, v in (base_env|extra_env).items())
    env_cmd = f"env {env_values}"

    return run.run(f"ssh {ssh_flags} -i {private_key_path} {user}@{host} -p {port} -- {env_cmd} {cmd}",
                   **run_kwargs)

def exists(path):
    if config.project.get_config("remote_host.run_locally", print=False):
        return path.exists()
    base_work_dir = prepare()

    ret = run_with_ansible_ssh_conf(
        base_work_dir,
        f"test -f {path}",
        capture_stdout=True,
        check=False,
    )

    return ret.returncode == 0
