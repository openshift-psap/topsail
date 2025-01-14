#! /usr/bin/python3

import sys, os
import subprocess
import logging
import pathlib

import ray
from ray.util.scheduling_strategies import NodeAffinitySchedulingStrategy

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

    os.environ["LD_LIBRARY_PATH"] = "./usr/lib64/"

    subprocess.run("./usr/bin/iperf3 --version", shell=True, check=True)

def init_ray():
    ray.init()


def run_iperf_server():
    return subprocess.Popen("./usr/bin/iperf3 -s -p 1234", shell=True) # need to detach it


def run_iperf_client():

    @ray.remote
    def run(server_ip):
        install_iperf()

        with open("/proc/sys/kernel/hostname") as f:
            print(f"Running from remote worker node {f.read().strip()}")

        os.environ["LD_LIBRARY_PATH"] = "/opt/app-root/src/usr/lib64/"
        subprocess.run(f"/opt/app-root/src/usr/bin/iperf3 -c {server_ip} -p 1234", shell=True, check=True)


    for node in ray.nodes():
        if node["NodeManagerHostname"] == os.environ["HOSTNAME"]: continue
        worker_node_id = node["NodeID"]
        logging.info(f"Running on {node['NodeManagerHostname']} ({worker_node_id})")
        break
    else:
        logging.fatal("Couldn't find a target worker node :/")
        raise SystemExit(1)

    server_ip = os.environ["MY_POD_IP"] # env var exposed by KubeRay

    wait = run.options(
        scheduling_strategy=NodeAffinitySchedulingStrategy(
            node_id=worker_node_id,
            soft=False,
        )).remote(server_ip)

    ray.wait([wait])


def main():
    install_iperf()
    init_ray()

    server = run_iperf_server()
    try:
        run_iperf_client()
    finally:
        server.kill()
        server.wait()


if __name__ == "__main__":
    sys.exit(main())
