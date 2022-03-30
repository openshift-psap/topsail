#! /usr/bin/python3

import logging
import os, sys

logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "DEBUG"),
    format="%(levelname)6s | %(message)s",
)

try:
    import fire
except ModuleNotFoundError:
    logging.error("WDM requires the Python `fire` package.")
    sys.exit(1)

import wdm.env_config as env_config
import wdm.main as wdm_main

# ---

def get_entrypoint(entrypoint_name):

    def entrypoint(dependency_file: str = "./dependencies.yaml",
                   target: str = "",
                   ansible_config: str = None,
                   library: bool = False,
                   config: str = "",
                   config_file: str = ""
                   ):
        """
Run Workload Dependency Manager

Modes:
    dryrun: do not run test nor install tasks.
    test: only test if a dependency is satisfied.
    ensure: test dependencies and install those unsatisfied.

Env:
    WDM_DEPENDENCY_FILE
    WDM_TARGET
    WDM_ANSIBLE_CONFIG
    WDM_CONFIG
    WDM_LIBRARY

Or stored in .wdm_env. See the `FLAGS` section for the descriptions.

Return codes:
    2 if an error occured
    1 if the testing is unsuccessful (test mode)
    1 if an installation failed (ensure mode)
    0 if the testing is successful (test mode)
    0 if the dependencies are all satisfied (ensure mode)

Args:
    dependency_file: Path of the dependency file to resolve.
    target: Dependency to resolve. If empty, take the first entry defined the dependency file.
    ansible_config: Ansible config file (for Ansible tasks).
    library: If True, the `dependency_file` can be omitted.
    config: comma-separated key=value list of configuration values.
    config_file: Path to a file containing configuration key=value pairs, one per line. If empty, loads '.wdm_config' if it exists, or 'no' to skip loading any config file.
"""
        kwargs = dict(locals()) # capture the function arguments

        env_config.update_env_with_env_files()
        env_config.update_kwargs_with_env(kwargs)

        wdm_dependency_file = kwargs["dependency_file"]

        return wdm_main.wdm_main(entrypoint_name, kwargs)

    return entrypoint

def show_example():
    """
    Show the example of command and files
    """
    print("""
Examples:
    $ export WDM_DEPENDENCY_FILE=...
    $ wdm test has_nfd
    $ wdm ensure has_gpu_operator
---
name: has_gpu_operator
spec:
  requirements:
  - has_nfd
  test:
  - name: has_nfd_operatorhub
    type: shell
    spec: oc get pod -l app.kubernetes.io/component=gpu-operator -A -oname
  install:
  - name: install_gpu_operator
    type: shell
    spec: ./run_toolbox.py gpu_operator deploy_from_operatorhub
  - name: install_gpu_operator
    type: shell
    spec: ./run_toolbox.py gpu_operator wait_deployment
---
name: has_nfd
spec:
  test:
  - name: has_nfd_labels
    type: shell
    spec: ./run_toolbox.py nfd has_labels
  install:
  - name: install_nfd_from_operatorhub
    type: shell
    spec: ./run_toolbox.py nfd_operator deploy_from_operatorhub
""")

class WDM_Entrypoint:
    def __init__(self):
        self.dryrun = get_entrypoint("dryrun")
        self.ensure = get_entrypoint("ensure")
        self.test = get_entrypoint("test")
        self.list = get_entrypoint("list")
        self.example = show_example

def main():
    # Print help rather than opening a pager
    fire.core.Display = lambda lines, out: print(*lines, file=out)

    # Launch CLI, get a runnable
    fire.Fire(WDM_Entrypoint())


if __name__ == "__main__":
    main()
