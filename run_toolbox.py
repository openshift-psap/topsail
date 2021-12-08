#!/usr/bin/env python3

import sys

try:
    import fire
except ModuleNotFoundError:
    print("The toolbox requires the Python `fire` package, see requirements.txt for a full list of requirements")
    sys.exit(1)

from toolbox.cluster import Cluster
from toolbox.entitlement import Entitlement
from toolbox.gpu_operator import GPUOperator
from toolbox.nfd import NFD
from toolbox.nfd_operator import NFDOperator
from toolbox.local_ci import LocalCI
from toolbox.repo import Repo
from toolbox.special_resource_operator import SpecialResourceOperator
from toolbox.benchmarking import Benchmarking
from toolbox.utils import Utils


class Toolbox:
    """
    The PSAP Operators Toolbox

    The toolbox is a set of tools, originally written for
    CI automation, but that appeared to be useful for a broader scope. It
    automates different operations on OpenShift clusters and operators
    revolving around PSAP activities: entitlement, scale-up of GPU nodes,
    deployment of the NFD, SRO and NVIDIA GPU Operators, but also their
    configuration and troubleshooting.
    """
    def __init__(self):
        self.cluster = Cluster
        self.entitlement = Entitlement
        self.gpu_operator = GPUOperator
        self.nfd_operator = NFDOperator
        self.nfd = NFD
        self.repo = Repo
        self.local_ci = LocalCI
        self.sro = SpecialResourceOperator
        self.benchmarking = Benchmarking
        self.utils = Utils

def main(no_exit=False):
    # Print help rather than opening a pager
    fire.core.Display = lambda lines, out: print(*lines, file=out)

    # Launch CLI, get a runnable
    runnable = None
    try:
        runnable = fire.Fire(Toolbox())
    except fire.core.FireExit:
        if not no_exit:
            raise

    # Run the actual workload
    try:
        if hasattr(runnable, "_run"):
            runnable._run()
        else:
            # CLI didn't resolve completely - either by lack of arguments
            # or use of `--help`. This is okay.
            pass
    except SystemExit as e:
        if not no_exit:
            sys.exit(e.code)


if __name__ == "__main__":
    main()
