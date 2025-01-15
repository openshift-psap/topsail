#! /usr/bin/python3

import sys, os
import subprocess
import logging
import pathlib

import ray
from ray.util.scheduling_strategies import NodeAffinitySchedulingStrategy

def config_logging():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

def install_iperf():
    if pathlib.Path("./usr/bin/iperf3").exists():
        logging.info("iperf3 already available, no need to download it.")
        return

    IPERF_VERSION = "3.9-9.el9"
    LKSCTP_VERSION = "1.0.19-2.el9"
    INSTALL_IPERF = f"""
wget --quiet https://rpmfind.net/linux/centos-stream/9-stream/AppStream/x86_64/os/Packages/iperf3-{IPERF_VERSION}.x86_64.rpm
rpm2archive iperf3-{IPERF_VERSION}.x86_64.rpm
tar xf iperf3-{IPERF_VERSION}.x86_64.rpm.tgz

wget --quiet https://rpmfind.net/linux/centos-stream/9-stream/BaseOS/x86_64/os/Packages/lksctp-tools-{LKSCTP_VERSION}.x86_64.rpm
rpm2archive lksctp-tools-{LKSCTP_VERSION}.x86_64.rpm
tar xf lksctp-tools-{LKSCTP_VERSION}.x86_64.rpm.tgz
"""

    subprocess.run(INSTALL_IPERF, shell=True, check=True)

    os.environ["LD_LIBRARY_PATH"] = "/opt/app-root/src/usr/lib64/"

    subprocess.run("/opt/app-root/src/usr/bin/iperf3 --version", shell=True, check=True)

def init_ray():
    ray.init()


def run_iperf_server(port):
    return subprocess.Popen(f"/opt/app-root/src/usr/bin/iperf3 -s -p {port}", shell=True) # need to detach it


def run_iperf_client(port):

    @ray.remote
    def run(server_ip, _port):
        install_iperf()

        with open("/proc/sys/kernel/hostname") as f:
            print(f"Running from remote worker node {f.read().strip()}")

        os.environ["LD_LIBRARY_PATH"] = "/opt/app-root/src/usr/lib64/"
        subprocess.run(f"/opt/app-root/src/usr/bin/iperf3 -c {server_ip} -p {_port}", shell=True, check=True)


    for node in ray.nodes():
        if node["NodeManagerHostname"] == os.environ["HOSTNAME"]: continue
        worker_node_id = node["NodeID"]
        logging.info(f"Running on {node['NodeManagerHostname']} ({worker_node_id})")
        break
    else:
        logging.fatal("Couldn't find a target worker node :/")
        raise SystemExit(1)

    server_ip = os.environ["MY_POD_IP"] # env var exposed by KubeRay
    nic_name = subprocess.run(f"echo $(ip route | grep '{server_ip}' | cut -d' ' -f3)", shell=True, check=True, capture_output=True).stdout.decode("ascii").strip()
    logging.info(f"Running the server on {server_ip} from {nic_name}")

    wait = run.options(
        scheduling_strategy=NodeAffinitySchedulingStrategy(
            node_id=worker_node_id,
            soft=False,
        )).remote(server_ip, port)

    ray.wait([wait])


def main():
    config_logging()

    install_iperf()
    init_ray()

    PORT = 1234
    server = run_iperf_server(PORT)
    try:
        run_iperf_client(PORT)
    finally:
        server.kill()
        server.wait()


if __name__ == "__main__":
    sys.exit(main())
