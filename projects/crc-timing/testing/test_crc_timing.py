import os, sys
import pathlib
import logging
import yaml
import uuid
import time
import shlex
import subprocess

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

def start_vfkit_vm(base_work_dir):
    _, _, vfkit_binary_path = prepare_crc_timing.get_crc_binary_path(base_work_dir)

    mac_addr = config.project.get_config("test.vm.hardware.mac_addr")

    machine_dir = base_work_dir / "crc" / "machine"
    diskfile = config.project.get_config('prepare.crc.bundle.diskfile')
    disk_path = machine_dir / diskfile

    user_data, meta_data = prepare_crc_timing.get_cloud_init_files(base_work_dir)

    with env.NextArtifactDir(f"start_vfkit"):
        remote_access.mkdir(env.ARTIFACT_DIR)

        vm_log_file_path = env.ARTIFACT_DIR / "vfkit_vm.log"
        log_file_path = env.ARTIFACT_DIR / "vfkit.log"
        vfkit_command = [
            f"nohup '{vfkit_binary_path}'",
            f"--cpus {config.project.get_config('test.vm.hardware.cpus')}",
            f"--memory {config.project.get_config('test.vm.hardware.memory')}",
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

    if not config.project.get_config('test.vm.reuse'):
        remote_access.run_with_ansible_ssh_conf(
            base_work_dir,
            " ".join(vfkit_command),
        )

    vfkit_pid = remote_access.read("/tmp/vfkit.pid").strip()
    logging.info(f"vfkit running with PID {int(vfkit_pid)} and logs stored in {log_file_path}")

    return get_vfkit_vm_ip(base_work_dir)

def get_vfkit_vm_ip(base_work_dir):
    mac_addr = config.project.get_config("test.vm.hardware.mac_addr")

    ip_addr = remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        f"cat /private/var/db/dhcpd_leases | grep 'address=1,{mac_addr}' -B1 | grep ip_address | cut -d= -f2",
        capture_stdout=True,
    )

    return ip_addr.stdout.strip()


def start_libvirt_vm(base_work_dir):
    machine_dir = base_work_dir / "crc" / "machine"
    diskfile = config.project.get_config('prepare.crc.bundle.diskfile')
    disk_path = machine_dir / diskfile
    mac_addr = config.project.get_config("test.vm.hardware.mac_addr")

    user_data, _ = prepare_crc_timing.get_cloud_init_files(base_work_dir)

    vm_name = "topsail-crc"

    virt_install_cmd = [
        "sudo virt-install",
        f"--name={vm_name}",
        f"--vcpus {config.project.get_config('test.vm.hardware.cpus')}",
        f"--memory {config.project.get_config('test.vm.hardware.memory')}",
        f"--disk path='{disk_path}',format=qcow2,bus=virtio",
        f"--cloud-init disable=on,user-data={user_data}",
        f"--network network=default,model=virtio,mac={mac_addr}",
        "--import --os-variant=generic --nographics --noautoconsole",
    ]

    if not config.project.get_config('test.vm.reuse'):
        remote_access.run_with_ansible_ssh_conf(
            base_work_dir,
            " ".join(virt_install_cmd),
        )

    return wait_libvirt_vm_network_ready(base_work_dir)


def start_vm(base_work_dir):
    hypervisor = config.project.get_config("prepare.crc.bundle.hypervisor")
    if hypervisor == "vfkit":
        return start_vfkit_vm(base_work_dir)

    elif hypervisor == "libvirt":
        return start_libvirt_vm(base_work_dir)
    else:
        raise ValueError(f"Unsupported hypervisor '{hypervisor}' configured for the bundle.")


def get_kubeadmin_pass_from_cloud_init(base_work_dir):
    user_data, _meta_data = prepare_crc_timing.get_cloud_init_files(base_work_dir)
    user_data_yaml = yaml.safe_load(remote_access.read(user_data))

    for file_descr in user_data_yaml["write_files"]:
        if file_descr["path"] == "/opt/crc/pass_kubeadmin":
            return file_descr["content"].strip()

    raise ValueError("Couldn't find the kubeadmin password in the cloud-init files ...")


def get_kubeadmin_pass_from_vm(base_work_dir, ip_addr):
    return execute_vm_command( # login on the VM as well
            base_work_dir, ip_addr,
            "sudo cat /opt/crc/pass_kubeadmin",
            handled_secretly=True,
            capture_stdout=True,
    ).stdout.strip()


def wait_vm_ping_ready(base_work_dir, ip_addr):
    remaining_tries = 60
    DELAY = 5

    logging.info("Waiting for the VM to respond to ping ...")
    while True:
        try:
            remote_access.run_with_ansible_ssh_conf(
                base_work_dir,
                f"ping -c 1 -W 1 '{ip_addr}'",
                handled_secretly=True, # to avoid the log spam
                capture_stdout=True,
            )
            logging.info("VM is responding to ping!")
            break
        except subprocess.CalledProcessError as e:
            logging.info(f"Ping failed ... {e}")
            pass
        remaining_tries -= 1
        if remaining_tries == 0:
            raise RuntimeError("Failed to ping the VM :/")

        logging.info(f"{remaining_tries} left. Sleeping {DELAY}s before retrying.")
        time.sleep(DELAY)


def wait_libvirt_vm_network_ready(base_work_dir):
    remaining_tries = 60
    DELAY = 10

    while True:
        try:
            logging.info(f"Waiting for the libvirt VM to receive an IP address ... {remaining_tries} tries left")

            out = remote_access.run_with_ansible_ssh_conf(
                base_work_dir,
                "sudo virsh domifaddr topsail-crc | tail -2 | head -1 | awk '{print $4}' | cut -d/ -f1",
                handled_secretly=True, # to avoid the log spam
                capture_stdout=True
            ).stdout.strip()
            if out:
                logging.info(f"Found the VM IP: {out}")
                return out

        except subprocess.CalledProcessError:
            logging.info("virsh domifaddr command failed ...")
            pass

        remaining_tries -= 1
        if remaining_tries == 0:
            raise RuntimeError("Failed to establish the connection to the VM :/")
        time.sleep(DELAY)


def wait_vm_ssh_ready(base_work_dir, ip_addr):
    remaining_tries = 60
    DELAY = 10

    while True:
        try:
            logging.info(f"Waiting for the VM to respond to SSH ... {remaining_tries} tries left")

            out = execute_vm_command(
                base_work_dir, ip_addr,
                "echo SUCCESS",
                ssh_timeout=1,
                #handled_secretly=True, # to avoid the log spam
                capture_stdout=True
            ).stdout

            if "SUCCESS" in out:
                logging.info(f"Waiting for the VM to respond to SSH ... succeeded!")
                break
            logging.info(f"command succedded but magic not found in '{out}' :/")
        except subprocess.CalledProcessError as e:
            logging.info("ssh test command failed ...")
            pass
        remaining_tries -= 1
        if remaining_tries == 0:
            raise RuntimeError("Failed to establish the connection to the VM :/")
        time.sleep(DELAY)


def wait_vm_crc_ready(base_work_dir, ip_addr):
    DELAY = 5*60 # 5min
    RETRY_DELAY = 10 # 10s
    start_time = time.time()
    while True:
        out = execute_vm_command(
            base_work_dir,
            ip_addr,
            # waits until propery crc-custom.target is active
            # `systemctl wait` not available yet in RHCOS
            "time sudo systemd-run --wait --unit=topsail-wait-system-ready --property=After=crc-custom.target /bin/true; ret=$?; [[ $ret == 0 ]] && echo SUCCESS || echo FAILED; exit $ret",
            capture_stdout=True
        ).stdout
        elapsed = int(time.time() - start_time)
        if "SUCCESS" in out:
            logging.info(f"wait_vm_crc_ready: ready after {elapsed}s")
            return
        elif "FAILED" in out:
            logging.info(f"wait_vm_crc_ready: FAILED after {elapsed}s")
            raise RuntimeError("'crc-custom.target' failed to get ready")
        else:
            logging.info(f"wait_vm_crc_ready: command not running after {elapsed}s")
            if elapsed > DELAY:
                raise RuntimeError("failed to check 'crc-custom.target' status ")

            # still time, wait and retry
            time.sleep(RETRY_DELAY)


def oc_login(base_work_dir, ip_addr):
    passwd = get_kubeadmin_pass_from_cloud_init(base_work_dir)
    oc = prepare_crc_timing.get_oc_binary_path(base_work_dir)

    # try:
    #     remote_access.run_with_ansible_ssh_conf( # login on the remote node
    #         base_work_dir,
    #         f"{oc} login https://{ip_addr}:6443 --username kubeadmin --password '{passwd}'",
    #         handled_secretly=True, # contains the kubeadmin pass
    #     )
    # except subprocess.CalledProcessError as e:
    #     logging.error("Failed to login into OCP from the host:/")
    #     raise

    try:
        execute_vm_command( # login on the VM as well
            base_work_dir, ip_addr,
            "mkdir -p .kube && cp /var/opt/kubeconfig .kube/config"
        )
    except subprocess.CalledProcessError as e:
        logging.error("Failed to login into OCP from the VM:/")
        raise


def execute_vm_command(base_work_dir, ip_addr, command, ssh_timeout=None, handled_secretly=False, capture_stdout=False, check=True):
    ssh_key = prepare_crc_timing.get_crc_ssh_private_key(base_work_dir)
    user = config.project.get_config("test.vm.ssh.user", print=False)
    ssh_args = " ".join(config.project.get_config("test.vm.ssh.args", print=False))

    remote_cmd = shlex.quote(command)
    return remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        (f"timeout {ssh_timeout} " if ssh_timeout else "") +
        f"ssh -i '{ssh_key}' {ssh_args} {user}@{ip_addr} {remote_cmd}",
        handled_secretly=handled_secretly,
        capture_stdout=capture_stdout,
        check=check,
    )


def get_remote_timestamp(base_work_dir):
    result = remote_access.run_with_ansible_ssh_conf(
        base_work_dir,
        "date -u +%Y-%m-%dT%H:%M:%SZ",
        capture_stdout=True,
    )
    return result.stdout.strip()

def test():
    base_work_dir = remote_access.prepare()

    if not config.project.get_config('test.vm.reuse'):
        prepare_crc_timing.stop_vm(base_work_dir)

    ip_addr = start_vm(base_work_dir)
    wait_vm_ping_ready(base_work_dir, ip_addr)
    ping_ready_ts = get_remote_timestamp(base_work_dir)

    wait_vm_ssh_ready(base_work_dir, ip_addr)
    ssh_ready_ts = get_remote_timestamp(base_work_dir)

    wait_vm_crc_ready(base_work_dir, ip_addr)
    oc_login(base_work_dir, ip_addr)

    with env.NextArtifactDir("crc_boot_timing"):
        remote_access.mkdir(env.ARTIFACT_DIR)

        remote_access.write(
            env.ARTIFACT_DIR / "topsail_checkpoints.txt",
            yaml.dump(dict(ping_ready_ts=ping_ready_ts, ssh_ready_ts=ssh_ready_ts))
        )


        """
echo 0 > exit_code
echo "test: true" > settings.yaml

systemctl status --failed > systemctl_status_failed
systemd-analyze critical-chain > systemd-analyze_critical-chain.txt
systemd-analyze critical-chain crc-custom.target > systemd-analyze_critical-chain_crc-custom.txt
systemd-analyze blame > systemd-analyze_blame.txt
systemd-analyze plot > systemd-analyze_plot.svg
systemd-analyze dump > systemd-analyze_dump.txt

oc get clusteroperators > oc-get-clusteroperators.txt
oc get clusteroperators -oyaml  > oc-get-clusteroperators.yaml
oc get clusterversion -oyaml > oc-get-clusterversion.yaml
oc get clusterversion > oc-get-clusterversion.txt

while read unit_name; do
   journalctl --boot --unit "$unit_name" > journalctl_u_${unit_name}.txt
done <<< "$(systemctl list-units --type=service --all | grep loaded | grep -E '(crc-|ocp-|cloud-)' | awk  '{print $1}')"
"""
        systemctl_status_failed = \
            execute_vm_command(base_work_dir, ip_addr,
                               "systemctl status --failed",
                               capture_stdout=True, check=False).stdout
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

        # Get list of CRC and OCP services
        all_services = execute_vm_command(
            base_work_dir, ip_addr,
            "systemctl list-units --type=service --all",
            capture_stdout=True
        ).stdout.strip()

        # Process each service
        for service_line in all_services.splitlines():
            if "loaded" not in service_line:
                continue

            # use the 'x' marker to ensure that the first word is either 'x' or 'x●', and the service is next
            unit_name = ("x"+service_line).split()[1]
            if not unit_name.endswith(".service"):
                continue

            if not (unit_name.startswith("crc-") or unit_name.startswith("ocp-") or unit_name.startswith("cloud-")):
                continue

            remote_access.write(
                env.ARTIFACT_DIR / f"journalctl_u_{unit_name}.txt",
                execute_vm_command(
                    base_work_dir, ip_addr,
                    f"journalctl --boot --unit {unit_name}",
                    capture_stdout=True
                ).stdout,
                handled_secretly=True,  # too verbose for the logs
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
