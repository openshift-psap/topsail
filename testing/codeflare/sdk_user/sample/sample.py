# Import pieces from codeflare-sdk
import logging

from codeflare_sdk.cluster.cluster import Cluster, ClusterConfiguration
from codeflare_sdk.job.jobs import DDPJobDefinition
from time import sleep

from common import env, config, run, visualize


def main():
    namespace = config.ci_artifacts.get_config("tests.sdk_user.namespace")
    user_idx = config.ci_artifacts.get_config("tests.sdk_user.user_index")
    user_count = config.ci_artifacts.get_config("tests.sdk_user.user_count")

    logging.info(f"Hello world, working with namespace {namespace} with {user_idx}/{user_count}")

    # Create our cluster and submit appwrapper
    cluster = Cluster(ClusterConfiguration(
        namespace=namespace, name=f"mnisttest-user{user_idx}",
        min_worker=2, max_worker=2,
        min_cpus=2, max_cpus=2,
        min_memory=4, max_memory=4,
        gpu=0,
        instascale=False))
    # Bring up the cluster
    cluster.up()
    cluster.wait_ready()
    cluster.status()
    cluster.details()


    job_def = DDPJobDefinition(name="mnisttest", script="mnist.py", workspace=".", scheduler_args={"requirements": "./requirements.txt"})
    job = job_def.submit(cluster)

    finished = False
    failed = False
    while not finished and not failed:
        sleep(1)
        status = job.status()
        finished = (str(status.state) == "SUCCEEDED")
        failed = (str(status.state) == "FAILED")

    print(job.logs())
    print(status)

    cluster.down()
