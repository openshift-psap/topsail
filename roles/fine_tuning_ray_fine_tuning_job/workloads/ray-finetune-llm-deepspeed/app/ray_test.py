from codeflare_sdk.cluster.cluster import Cluster, ClusterConfiguration
from codeflare_sdk.cluster.auth import TokenAuthentication
import os
import sys


from codeflare_sdk import KubeConfigFileAuthentication

auth = KubeConfigFileAuthentication(kube_config_path="/tmp/kubeconfig")
auth.load_kube_config()


# Configure the Ray cluster
cluster = Cluster(ClusterConfiguration(
    name='ray',
    namespace='fine-tuning-testing',
    num_workers=7,
    worker_cpu_requests=16,
    worker_cpu_limits=16,
    head_cpu_requests=16,
    head_cpu_limits=16,
    worker_memory_requests=120,
    worker_memory_limits=256,
    head_memory_requests=100,
    head_memory_limits=120,
    # Use the following parameters with NVIDIA GPUs
    image="quay.io/rhoai/ray:2.35.0-py39-cu121-torch24-fa26",
    head_extended_resource_requests={'nvidia.com/gpu':1},
    worker_extended_resource_requests={'nvidia.com/gpu':1},

    # Or replace them with these parameters for AMD GPUs
    # image="quay.io/rhoai/ray:2.35.0-py39-rocm61-torch24-fa26",
    # head_extended_resource_requests={'amd.com/gpu':1},
    # worker_extended_resource_requests={'amd.com/gpu':1},
))
try:
    cluster.down()
except: pass

cluster.up()
cluster.wait_ready()
