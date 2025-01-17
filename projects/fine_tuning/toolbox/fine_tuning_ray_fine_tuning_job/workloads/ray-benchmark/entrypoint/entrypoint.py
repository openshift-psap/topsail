#! /usr/bin/python3

import os, sys
import json, yaml
import pathlib
import logging
import subprocess

def config_logging():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

def main():
    config_json_path = os.environ.get("CONFIG_JSON_PATH")
    if not config_json_path:
        logging.fatal("Env var CONFIG_JSON_PATH must point to the config file.")
        return 1

    with open(pathlib.Path(config_json_path)) as f:
        config = json.load(f)

    flavor = config.get("flavor")

    print(f"Running with {flavor}.")

    app_script = pathlib.Path(f"/mnt/app/test_{flavor}.py")

    if not app_script.exists():
        logging.fatal(f"App script for flavor {flavor} doesn't exist :/ ({app_script})")
        return 1

    env = os.environ.copy()
    if secondary_socket_ifname := os.environ.get("SECONDARY_SOCKET_IFNAME"):
        names = secondary_socket_ifname.split(",")
        ifname = names[0]
        if len(names) > 1:
            logging.warning(f"Multiple secondary NICs received. Taking the first one: {ifname}.")
        ip_addr = subprocess.run(f"ip route | grep ' {ifname} ' | cut -d' ' -f9", shell=True, check=True, capture_output=True).stdout.decode("ascii").strip()
        env["MY_POD_IP"] = ip_addr
        logging.info(f"Using MY_POD_IP={ip_addr} ({ifname} secondary NIC)")

    subprocess.run(f"python3 '{app_script}'", shell=True, check=True, env=env)

    return 0


if __name__ == "__main__":
    config_logging()

    retcode = main()

    import time
    time.sleep(10)

    if retcode == 0:
        print("SCRIPT SUCCEEDED")
    else:
        print("SCRIPT FAILED")

    # always exit 0, otherwise the RayJob retries 3 times :/
    sys.exit(0)
