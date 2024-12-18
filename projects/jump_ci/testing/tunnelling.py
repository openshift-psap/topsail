import time
import pathlib
import logging
import os
import functools
import atexit
import time
import subprocess
import yaml

from projects.core.library import env, config, run, configure_logging

from projects.jump_ci.testing import utils

extra_vars_file = None

@utils.entrypoint()
def prepare(
        verbose=None,
):
    """
    Prepare the environment for running TOPSAIL in the jump host

    Args:
      verbose: if enabled, displays additional info. *Will display SSH host names*.
    """

    LOCAL_HOST_PORT = config.project.get_config("ssh_tunnel.local_host_port")
    SECRET_ENV_KEY = config.project.get_config("secrets.dir.env_key")
    PRIVATE_KEY_FILENAME = config.project.get_config("secrets.private_key_filename")
    BASTION_HOST_FILENAME = config.project.get_config("secrets.bastion_host_filename")
    JUMP_HOST_FILENAME = config.project.get_config("secrets.jump_host_filename")
    SSH_FLAGS = config.project.get_config("ssh.flags")

    private_key_path = pathlib.Path(os.environ[SECRET_ENV_KEY]) / PRIVATE_KEY_FILENAME

    if verbose is None:
        verbose = config.project.get_config("ssh_tunnel.verbose")

    with open(pathlib.Path(os.environ[SECRET_ENV_KEY]) / BASTION_HOST_FILENAME) as f:
        bastion_user, _, bastion_host = f.readline().strip().rpartition("@") # strip any username in the hostname

    if config.project.get_config("ssh_tunnel.enabled"):
        logging.info("ssh_tunnel.enabled is set, creating a tunnel to the bastion via the jump host")
        # creates a tunnel to the jumphost to the bastion, on localhost:2500

        open_tunnel(
            secret_env_key=SECRET_ENV_KEY,
            private_key_filename=PRIVATE_KEY_FILENAME,
            bastion_host_filename=BASTION_HOST_FILENAME,
            local_host_port=LOCAL_HOST_PORT,

            jump_host_filename=JUMP_HOST_FILENAME,
            verbose=verbose,
            keep_open=False,
            ssh_flags=SSH_FLAGS,
        )

        remote_host = "localhost"
        remote_host_port = LOCAL_HOST_PORT
    else:
        logging.info("ssh_tunnel.enabled is disabled, connecting directly to the bastion")
        remote_host = bastion_host
        remote_host_port = 22
        # probe_ssh_endpoint(
        #     bastion_user,
        #     bastion_host,
        #     remote_host_port,
        #     private_key_path,
        #     SSH_FLAGS,
        #     verbose,
        # )

    os.environ["TOPSAIL_JUMP_CI_REMOTE_HOST"] = remote_host

    extra_vars_fd_path, extra_vars_file = utils.get_tmp_fd()

    os.environ["TOPSAIL_ANSIBLE_PLAYBOOK_EXTRA_VARS"] = extra_vars_fd_path

    extra_vars_yaml_content = f"""
ansible_port: {remote_host_port}
ansible_ssh_private_key_file: {private_key_path}
ansible_ssh_user: {bastion_user}
ansible_ssh_common_args: "{' '.join(SSH_FLAGS)}"
"""
    print(extra_vars_yaml_content, file=extra_vars_file)
    extra_vars_file.flush()


@utils.entrypoint()
def open_tunnel(
        secret_env_key="PSAP_ODS_SECRET_PATH",
        private_key_filename="jumpci_privatekey",
        jump_host_filename="jumpci_jump_host",
        local_host_port=2500,
        bastion_host_filename="jumpci_bastion_host",
        bastion_host_port=22,
        verbose=False,
        keep_open=True,
        ssh_flags=[],
):
    """
    Tests the tunnel to access the jump host.

    Args:
      secret_env_key: name of the env key pointing to the secret directory
      private_key_filename: name of the secret file in the secret directory
      jump_host_filename: ssh name of the jump host
      local_host_port: port to open locally
      bastion_host_filename: name of the secret file with the hostname of the bastion host
      bastion_host_port: port to redirect in the target host
      verbose: if enabled, shows the tunnel command
      keep_open: if disabled, closes the tunnel when the Python process exits
      ssh_flags: extra flags to pass to SSH
    """

    secret_dir = pathlib.Path(os.environ[secret_env_key])

    private_key_path = secret_dir / private_key_filename

    with open(secret_dir / jump_host_filename) as f:
        jump_host = f.readline().strip()

    with open(secret_dir / bastion_host_filename) as f:
        bastion_user, _, bastion_host = f.readline().strip().rpartition("@") # strip any username in the hostname

    # warning: this command doesn't fail ...
    cmd = f"ssh {' '.join(ssh_flags)} \
    -i {private_key_path} {jump_host} \
    -L {local_host_port}:{bastion_host}:{bastion_host_port} \
    -N"

    if verbose:
        logging.info(cmd)

    proc = subprocess.Popen(cmd, shell=True)

    if not keep_open:
        atexit.register(proc.kill)

    RETRIES = 150
    DELAY = 5
    logging.info("Waiting for the SSH connection to work ...")
    time.sleep(3)
    for i in range(RETRIES):
        try:
            probe_ssh_endpoint(bastion_user, "localhost", local_host_port, private_key_path, ssh_flags, verbose)
            logging.info(f"SSH connection working!")
            break
        except subprocess.CalledProcessError:
            logging.info(f"Attempt {i+1}/{RETRIES} failed ...")
            if i == (RETRIES - 1):
                raise Exception("SSH connection probe failed :/")
            time.sleep(DELAY)

    return

def probe_ssh_endpoint(user, host, port, private_key_path, ssh_flags, verbose):
    run.run(f"ssh {' '.join(ssh_flags)} -i {private_key_path} {user + '@' if user else ''}{host} -p {port} true",
            capture_stderr=True,
            log_command=verbose)

def run_with_ansible_ssh_conf(cmd):
    with open(os.environ["TOPSAIL_ANSIBLE_PLAYBOOK_EXTRA_VARS"]) as f:
        ansible_ssh_config = yaml.safe_load(f)

    ssh_flags = ansible_ssh_config["ansible_ssh_common_args"]
    host = os.environ["TOPSAIL_JUMP_CI_REMOTE_HOST"]
    port = ansible_ssh_config["ansible_port"]
    user = ansible_ssh_config["ansible_ssh_user"]
    private_key_path = ansible_ssh_config["ansible_ssh_private_key_file"]

    logging.info(f"Running on the jump host: {cmd}")
    run.run(f"ssh {ssh_flags} -i {private_key_path} {user}@{host} -p {port} -- {cmd}",
            log_command=False)
