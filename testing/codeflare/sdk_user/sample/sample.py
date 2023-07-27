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

    name = config.ci_artifacts.get_config("tests.sdk_user.ray_cluster.name")
    workers = config.ci_artifacts.get_config("tests.sdk_user.ray_cluster.workers")
    cpu = config.ci_artifacts.get_config("tests.sdk_user.ray_cluster.cpu")
    memory = config.ci_artifacts.get_config("tests.sdk_user.ray_cluster.memory")
    gpu = config.ci_artifacts.get_config("tests.sdk_user.ray_cluster.gpu")

    image = config.ci_artifacts.get_config("tests.sdk_user.ray_cluster.image")

    # Create our cluster and submit appwrapper
    cluster = Cluster(ClusterConfiguration(
        namespace=namespace, name=f"{name}-user{user_idx}",
        image=image,
        min_worker=workers, max_worker=workers,
        min_cpus=cpu, max_cpus=cpu,
        min_memory=memory, max_memory=memory,
        gpu=gpu, instascale=False))


    # Bring up the cluster
    cluster.up()
    cluster.wait_ready()
    cluster.status()
    cluster.details()

    job_name = config.ci_artifacts.get_config("tests.sdk_user.job.name")
    job_script = config.ci_artifacts.get_config("tests.sdk_user.job.script")

    job_def = DDPJobDefinition(name=job_name,
                               script=job_script,
                               workspace=".",
                               scheduler_args={"requirements": "./requirements.txt"})
    job = job_def.submit(cluster)

    finished = False
    failed = False
    while not finished and not failed:
        sleep(1)
        status = job.status()
        finished = (str(status.state) == "SUCCEEDED")
        failed = (str(status.state) == "FAILED")

    with open(f"{name}-{job_name}.log", "w") as f:
        print(job.logs(), file=f)

    print(status)

    cluster.down()
