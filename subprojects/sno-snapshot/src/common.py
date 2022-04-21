import time, datetime
import urllib3

print("Importing OpenShift/Kubernetes packages ...")

import kubernetes
import ocp_resources
import openshift

import ocp_resources.node
import ocp_resources.machine

import openshift.dynamic

print("Importing AWS boto3 ...")

import boto3
import botocore

client_k8s = None
client_ec2 = None
resource_ec2 = None

def configure():
    #
    # K8s
    #

    global client_k8s
    try:
        client_k8s = openshift.dynamic.DynamicClient(client=kubernetes.config.new_client_from_config())
    except Exception as e:
        print("WARNING: kubernetes not available:", e)

    #
    # AWS
    #

    machines = [m for m in ocp_resources.machine.Machine.get(dyn_client=client_k8s)]
    if not machines:
        raise RuntimeError("No machine available ...")
    cluster_region = machines[0].instance.spec.providerSpec.value.placement.region

    global client_ec2, resource_ec2
    cfg = botocore.config.Config(region_name=cluster_region)
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html
    client_ec2 = boto3.client('ec2', config=cfg)
    resource_ec2 = boto3.resource('ec2', config=cfg)

    print("Ready.")

def wait_openshift():
    first = True
    print("Waiting for OpenShift cluster to be ready ...")

    while True:
        try:
            global client_k8s
            client_k8s = DynamicClient(client=kubernetes.config.new_client_from_config())

            nodes = [m for m in ocp_resources.node.Node.get(dyn_client=client_k8s)]
            if len(nodes) != 0:
                print(f"Found {len(nodes)} node, OpenShift Cluster is ready!")
                break
        except urllib3.exceptions.MaxRetryError: pass
        except kubernetes.client.exceptions.ApiException: pass

        time.sleep(10)

def get_machine_props():
    if not client_k8s:
        return None, None

    machines = [m for m in ocp_resources.machine.Machine.get(dyn_client=client_k8s)]
    if len(machines) != 1:
        raise RuntimeError("Should be only one machine ...")

    machine = machines[0]

    cluster_name = machine.cluster_name
    print(f"Cluster name: {cluster_name}")

    instance = resource_ec2.Instance(machine.instance.status.providerStatus.instanceId)
    instance.load()
    print(f"Instance Id: {instance.id}")

    zone = machine.instance.spec.providerSpec.value.placement.availabilityZone
    print(f"Availability zone: {zone}")
    return cluster_name, instance, zone


def get_instance_root_volume(instance):
    volumes = [v for v in instance.volumes.all()]
    if len(volumes) > 1:
        print("WARNING: more than 1 volume found ...")

    return volumes[0]

def get_cluster_snapshot(cluster_name, instance, zone):
    resp = client_ec2.describe_snapshots(
        Filters=[{
            'Name': f'tag:kubernetes.io/cluster/{cluster_name}',
            'Values': ['owned']
        }])

    snapshots = resp["Snapshots"]
    if len(snapshots) == 0:
        return None

    if len(snapshots) > 1:
        print("WARNING: more than 1 snapshot found ... taking the first one.")

    snapshot = resource_ec2.Snapshot(snapshots[0]['SnapshotId'])
    snapshot.load()

    return snapshot

def await_snapshot(snapshot):
    prev = ""
    if snapshot.progress == "100%":
        print(f"Snapshot {snapshot.id} is ready.")

    while not snapshot.progress == "100%":
        if prev == "":
            print(f"Awaiting for the completion of snapshot {snapshot.id} ...")
            print(snapshot.progress)
            prev = snapshot.progress

        time.sleep(10)
        snapshot.reload()
        if prev != snapshot.progress:
            prev = snapshot.progress
            print(snapshot.progress)

def human_ts():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")
