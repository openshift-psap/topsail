import os, sys
import pathlib
import logging
import yaml
import uuid
import time

from projects.remote.lib import remote_access
from projects.core.library import env, config, run, configure_logging, export
from projects.matrix_benchmarking.library import visualize, matbenchmark

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
TOPSAIL_DIR = pathlib.Path(config.__file__).parents[3]
CRC_MAC_AI_SECRET_PATH = pathlib.Path(os.environ.get("CRC_MAC_AI_SECRET_PATH", "/env/CRC_MAC_AI_SECRET_PATH/not_set"))

# not using `os.getcwd()` anymore because of
# https://stackoverflow.com/questions/1542803/is-there-a-version-of-os-getcwd-that-doesnt-dereference-symlinks
RUN_DIR = pathlib.Path(os.getenv('PWD')) # for run_one_matbench
os.chdir(TOPSAIL_DIR)

import prepare_crc_timing

def start_macos_vm(base_work_dir):
    _, _, vfkit_binary_path = prepare_crc_timing.get_crc_binary_path(base_work_dir)

    try:
        old_vfkit_pid = remote_access.read("/tmp/vfkit.pid").strip()
    except Exception:
        old_vfkit_pid = None

    mac_addr = config.project.get_config("test.vm.mac_addr")

    machine_dir = base_work_dir / "crc" / "machine"
    disk_path = machine_dir / "crc.img"

    user_data, meta_data = prepare_crc_timing.get_cloud_init_files(base_work_dir)

    with env.NextArtifactDir(f"start_vfkit"):
        remote_access.mkdir(env.ARTIFACT_DIR)

        vm_log_file_path = env.ARTIFACT_DIR / "vfkit_vm.log"
        log_file_path = env.ARTIFACT_DIR / "vfkit.log"
        vfkit_command = [
            f"nohup '{vfkit_binary_path}'",
            f"--cpus {config.project.get_config('test.vm.cpus')}",
            f"--memory {config.project.get_config('test.vm.memory')}",
            f"--bootloader efi,variable-store={machine_dir}/efistore.nvram,create",
            f"--device 'virtio-serial,logFilePath={vm_log_file_path}'",
            "--device virtio-rng",
            f"--cloud-init '{user_data},{meta_data}'",
            f"--device 'virtio-blk,path={disk_path}'",
            f"--device 'virtio-net,nat,mac={mac_addr}'",
            "--timesync vsockPort=1234",
            f">{log_file_path} 2>&1 &\n",
            "echo $! > /tmp/vfkit.pid\n",
        ]

        remote_access.write(
            env.ARTIFACT_DIR / "vfkit.cmd",
            " ".join(vfkit_command)
        )


    if old_vfkit_pid:
        remote_access.run_with_ansible_ssh_conf(
            base_work_dir,
            f"kill -9 {int(old_vfkit_pid)}", # will raise an exception if pid isn't an int
            check=False,
        )

    remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        " ".join(vfkit_command),
    )

    vfkit_pid = remote_access.read("/tmp/vfkit.pid").strip()
    logging.info(f"vfkit running with PID {int(vfkit_pid)} and logs stored in {log_file_path}")


def get_vm_ip(base_work_dir):
    mac_addr = config.project.get_config("test.vm.mac_addr")

    ip_addr = remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"cat /private/var/db/dhcpd_leases | grep 'address=1,{mac_addr}' -B1 | grep ip_address | cut -d= -f2",
        capture_stdout=True,
    )

    return ip_addr.stdout.strip()


def start_vm(base_work_dir):
    start_macos_vm(base_work_dir)
    return get_vm_ip(base_work_dir)


def get_kubeadmin_pass_from_cloud_init(base_work_dir):
    user_data, _meta_data = prepare_crc_timing.get_cloud_init_files(base_work_dir)
    user_data_yaml = yaml.safe_load(remote_access.read(user_data))

    for file_descr in user_data_yaml["write_files"]:
        if file_descr["path"] == "/opt/crc/pass_kubeadmin":
            return file_descr["content"].strip()

    raise ValueError("Couldn't file the kubeadmin password in the cloud-init files ...")

def get_kubeadmin_pass_from_vm(base_work_dir, ip_addr):
    return execute_vm_command( # login on the VM as well
            base_work_dir, ip_addr,
            "sudo cat /opt/crc/pass_kubeadmin",
            handled_secretly=True,
            capture_stdout=True,
    ).stdout.strip()

def wait_vm_ssh_ready(base_work_dir, ip_addr):
    remaining_tries = 20
    DELAY = 10

    logging.info("Waiting for the VM to respond to SSH ...")
    while True:
        try:
            execute_vm_command(
                base_work_dir, ip_addr,
                "exit 0",
                ssh_timeout=1,
                handled_secretly=True, # to avoid the log spam
            )
            break
        except Exception:
            pass
        remaining_tries -= 1
        if remaining_tries == 0:
            raise RuntimeError("Failed to establish the connection to the VM :/")
        time.sleep(DELAY)


def wait_vm_crc_ready(base_work_dir, ip_addr):
    try:
        execute_vm_command(
            base_work_dir,
            ip_addr,
            # waits until propery crc-custom.target is active
            # `systemctl wait` not available yet in RHCOS
            "time sudo systemd-run --wait --unit=topsail-wait-system-ready --property=After=crc-custom.target /bin/true"
        )
    except Exception as e:
        logging.error("Failed to wait for CRC in the VM to get ready:/")
        raise


def oc_login(base_work_dir, ip_addr):
    passwd = get_kubeadmin_pass_from_cloud_init(base_work_dir)
    oc = prepare_crc_timing.get_oc_binary_path(base_work_dir)

    try:
        remote_access.run_with_ansible_ssh_conf( # login on the remote node
            base_work_dir,
            f"{oc} login https://{ip_addr}:6443 --username kubeadmin --password '{passwd}'",
            handled_secretly=True, # contains the kubeadmin pass
        )
    except Exception as e:
        logging.error("Failed to login into OCP from the host:/")
        raise

    try:
        execute_vm_command( # login on the VM as well
            base_work_dir, ip_addr,
            f"oc login https://localhost:6443 --username kubeadmin --password '{passwd}' --insecure-skip-tls-verify=true",
            handled_secretly=True, # contains the kubeadmin pass
        )
    except Exception as e:
        logging.error("Failed to login into OCP from the VM:/")
        raise



def execute_vm_command(base_work_dir, ip_addr, command, ssh_timeout=None, handled_secretly=False, capture_stdout=False):
    ssh_key = prepare_crc_timing.get_crc_ssh_private_key(base_work_dir)
    user = config.project.get_config("test.vm.ssh.user", print=False)
    ssh_args = " ".join(config.project.get_config("test.vm.ssh.args", print=False))

    return remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        (f"timeout {ssh_timeout} " if ssh_timeout else "") +
        f"ssh -i '{ssh_key}' {ssh_args} {user}@{ip_addr} {command}",
        handled_secretly=handled_secretly,
        capture_stdout=capture_stdout,
    )


def test():
    base_work_dir = remote_access.prepare()
    ip_addr = start_vm(base_work_dir)
    wait_vm_ssh_ready(base_work_dir, ip_addr)
    wait_vm_crc_ready(base_work_dir, ip_addr)
    oc_login(base_work_dir, ip_addr)

    oc = prepare_crc_timing.get_oc_binary_path(base_work_dir)

    with env.NextArtifactDir("crc_boot_timing"):
        remote_access.mkdir(env.ARTIFACT_DIR)

        systemctl_status_failed = \
            execute_vm_command(base_work_dir, ip_addr,
                               "systemctl status --failed",
                               capture_stdout=True).stdout
        if systemctl_status_failed.strip(): # save the file only if some services have failed
            remote_access.write(
                env.ARTIFACT_DIR / "systemctl_status_failed",
                systemctl_status_failed,
            )

        remote_access.write(
            env.ARTIFACT_DIR / "systemd-analyze_critical-chain.txt",
            execute_vm_command(base_work_dir, ip_addr,
                               "systemd-analyze critical-chain",
                               capture_stdout=True).stdout,
        )

        remote_access.write(
            env.ARTIFACT_DIR / "systemd-analyze_critical-chain_crc-custom.txt",
            execute_vm_command(base_work_dir, ip_addr,
                               "systemd-analyze critical-chain crc-custom.target",
                               capture_stdout=True).stdout,
        )
        remote_access.write(
            env.ARTIFACT_DIR / "systemd-analyze.txt",
            execute_vm_command(base_work_dir, ip_addr,
                               "systemd-analyze",
                               capture_stdout=True).stdout,
        )
        remote_access.write(
            env.ARTIFACT_DIR / "systemd-analyze_blame.txt",
            execute_vm_command(base_work_dir, ip_addr,
                               "systemd-analyze blame",
                               capture_stdout=True).stdout,
            handled_secretly=True, # too verbose for the logs
        )
        remote_access.write(
            env.ARTIFACT_DIR / "systemd-analyze_plot.svg",
            execute_vm_command(base_work_dir, ip_addr,
                               "systemd-analyze plot",
                               capture_stdout=True).stdout,
            handled_secretly=True, # too verbose for the logs
        )
        remote_access.write(
            env.ARTIFACT_DIR / "systemd-analyze_dump.txt",
            execute_vm_command(base_work_dir, ip_addr,
                               "systemd-analyze dump",
                               capture_stdout=True).stdout,
            handled_secretly=True, # too verbose for the logs
        )
        remote_access.write(
            env.ARTIFACT_DIR / "oc-get-clusteroperators.yaml",
            execute_vm_command(base_work_dir, ip_addr,
                               "oc get clusteroperators -oyaml",
                               capture_stdout=True).stdout,
            handled_secretly=True, # too verbose for the logs
        )
        remote_access.write(
            env.ARTIFACT_DIR / "oc-get-clusteroperators.txt",
            execute_vm_command(base_work_dir, ip_addr,
                               "oc get clusteroperators",
                               capture_stdout=True).stdout,
        )
        remote_access.write(
            env.ARTIFACT_DIR / "oc-get-clusterversion.yaml",
            execute_vm_command(base_work_dir, ip_addr,
                               "oc get clusterversion -oyaml",
                               capture_stdout=True).stdout,
            handled_secretly=True, # too verbose for the logs
        )
        remote_access.write(
            env.ARTIFACT_DIR / "oc-get-clusterversion.txt",
            execute_vm_command(base_work_dir, ip_addr,
                               "oc get clusterversion",
                               capture_stdout=True).stdout,
        )

        remote_access.write(
            env.ARTIFACT_DIR / "exit_code",
            "0",
        )

        remote_access.write(
            env.ARTIFACT_DIR / "settings.yaml",
            "test: true",
        )

    return 0


def generate_visualization(test_artifact_dir):
    exc = None

    with env.NextArtifactDir("plots"):
        exc = run.run_and_catch(exc, visualize.generate_from_dir, test_artifact_dir)

        logging.info(f"Test visualization has been generated into {env.ARTIFACT_DIR}/reports_index.html")

    return exc
