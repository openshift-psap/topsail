from toolbox.cluster import Cluster
from toolbox.entitlement import Entitlement
from toolbox.gpu_operator import GPUOperator
from toolbox.nfd import NFD
from toolbox.nfd_operator import NFDOperator
from toolbox.repo import Repo
from toolbox.benchmarking import Benchmarking
from toolbox.utils import Utils
from toolbox.rhods import RHODS
from toolbox.pipelines import Pipelines
from toolbox.wisdom import Wisdom
from toolbox.from_config import FromConfig
from toolbox.local_ci import Local_CI
from toolbox.load_aware import LoadAware

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
        self.benchmarking = Benchmarking
        self.utils = Utils
        self.rhods = RHODS
        self.pipelines = Pipelines
        self.from_config = FromConfig.run
        self.local_ci = Local_CI
        self.wisdom = Wisdom
        self.load_aware = LoadAware
