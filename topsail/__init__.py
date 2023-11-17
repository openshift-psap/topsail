from topsail.cluster import Cluster
from topsail.entitlement import Entitlement
from topsail.gpu_operator import GPU_Operator
from topsail.nfd import NFD
from topsail.nfd_operator import NFDOperator
from topsail.repo import Repo
from topsail.benchmarking import Benchmarking
from topsail.utils import Utils
from topsail.rhods import RHODS
from topsail.notebooks import Notebooks
from topsail.pipelines import Pipelines
from topsail.wisdom import Wisdom
from topsail.from_config import FromConfig
from topsail.local_ci import Local_CI
from topsail.load_aware import Load_Aware
from topsail.codeflare import Codeflare
from topsail.watsonx_serving import Watsonx_Serving
from topsail.llm_load_test import Llm_load_test

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
        self.gpu_operator = GPU_Operator
        self.nfd_operator = NFDOperator
        self.nfd = NFD
        self.repo = Repo
        self.benchmarking = Benchmarking
        self.utils = Utils
        self.rhods = RHODS
        self.notebooks = Notebooks
        self.pipelines = Pipelines
        self.from_config = FromConfig.run
        self.local_ci = Local_CI
        self.wisdom = Wisdom
        self.load_aware = Load_Aware
        self.codeflare = Codeflare
        self.watsonx_serving = Watsonx_Serving
        self.llm_load_test = Llm_load_test
