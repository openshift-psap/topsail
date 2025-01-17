#! /usr/bin/python3

import os, sys
import json, yaml
import pathlib
import logging
import subprocess

def update_ip_addresses():
    nic_remapped = pathlib.Path("/tmp/nic_remapped")
    if nic_remapped.exists():
        logging.info("The NICs have already been remapped. Skipping the remapping.")
        return

    nic_remapped.touch()

    with open("/mnt/nic-mapping/nodename_ip_mapping.yaml") as f:
        mapping = yaml.safe_load(f)

    for secondary_nic in mapping[os.environ["NODE_HOSTNAME"]]:
        ifname = secondary_nic["container_nic_name"]
        correct_ip = secondary_nic["ip"]
        current_ip = subprocess.run(f"ip route | grep '{ifname} ' | cut -d' ' -f9", shell=True, check=True, capture_output=True).stdout.decode("ascii").strip()

        logging.info(f"Remapping NIC {ifname} from {current_ip} to {correct_ip}")
        subprocess.run(f"ip addr del {current_ip}/24 dev {ifname}", shell=True, check=True)
        subprocess.run(f"ip addr add {correct_ip}/24 dev {ifname}", shell=True, check=True)

    if len(mapping[os.environ["NODE_HOSTNAME"]]) > 1:
        logging.warning("Detected multiple secondary network. Passing only the last one with MY_POD_IP.")


if __name__ == "__main__":
    logging.info("TOPSAIL Ray container initialization.")

    if os.environ.get("SECONDARY_SOCKET_IFNAME"):
        logging.info("TOPSAIL Ray container initialization: running update_ip_addresses()")
        update_ip_addresses()

    logging.info("TOPSAIL Ray container initialization: all done.")
