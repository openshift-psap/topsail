import sys
import datetime
import boto3
import botocore.config
from collections import defaultdict

IGNORE_LESS_THAN_DAYS = 0
MY_REGIONS = ["us-east-2", "us-east-1", "us-west-2", "eu-central-1"]
now = datetime.datetime.now(datetime.timezone.utc)

client_ec2 = boto3.client('ec2')
resource_ec2 = boto3.resource('ec2')

clusters = defaultdict(list)

IGNORE_NODES = [
    "Liquan-rhel82-jumphost",
    "walid-rhel82-jumphost1",
    "Lena-jumphost-rhel-8.2",
    "walid-arm64-rhel82-jumphost",
    "walid-arm64-jumphost",
]

IGNORE_CLUSTERS = [
    "walid4107p-2wx7t"
]

def collect_instances(region=None):
    print(f"Looking at the {region} region ...")

    if region is None:
        regional_resource_ec2 = resource_ec2
    else:
        my_config = botocore.config.Config(region_name=region)
        regional_resource_ec2 = boto3.resource("ec2", config=my_config)

    instance_count = 0
    instances_stopped = 0
    instances_ignored_too_young = 0
    instances_ignored_from_list = 0
    instances_ignored_terminated = 0
    for instance in regional_resource_ec2.instances.all():
        age = (now - instance.launch_time).days
        instance_count += 1

        if age < IGNORE_LESS_THAN_DAYS:
            instances_ignored_too_young += 1
            continue

        state = instance.state['Name']

        if state == "terminated":
            instances_ignored_terminated += 1
            continue

        if state == "stopped":
            instances_stopped += 1

        info = {
            "ID": instance.id,
            "Type": instance.instance_type,
            "State": instance.state["Name"],
            "Age": f"{age} days",
            "Region": region,
            "Name": "<not defined>",
        }

        for tag in instance.tags or {}:
            if tag["Key"] == "Name":
                info["Name"] = tag["Value"]
            if tag["Value"] == "owned":
                info["Cluster ID"] = tag["Key"]

        if info["Name"] in IGNORE_NODES:
            instances_ignored_from_list += 1
            continue

        if info.get("Cluster ID", None) in IGNORE_CLUSTERS:
            instances_ignored_from_list += 1
            continue

        clusters[info.get("Cluster ID")].append(info)
    if not instance_count: return
    print(f"""\
{instance_count=}
{instances_stopped=}
{instances_ignored_terminated=}
{instances_ignored_too_young=}
{instances_ignored_from_list=}
    """)

def get_all_regions():
    if MY_REGIONS:
        return MY_REGIONS

    return [region['RegionName'] for region in client_ec2.describe_regions()['Regions']]

def print_clusters():
    for cluster_tag in reversed(sorted(map(str, clusters))):
        if cluster_tag == "None":
            cluster_name = "Not part of a cluster"
            cluster_tag = None
        else:
            cluster_name = cluster_tag.rpartition("/")[-1]

        print(cluster_name)
        print("="*len(cluster_name))
        first = True
        for cluster_instance in clusters[cluster_tag]:

            if cluster_tag is not None:
                cluster_instance = dict(cluster_instance) # make a copy of the dict
                cluster_instance.pop('Cluster ID')
                cluster_instance['Name'] = cluster_instance['Name'].replace(f"{cluster_tag}-", "")
                if first:
                    print("Age:", cluster_instance['Age'])
                    print("Region:", cluster_instance['Region'])

            print(cluster_instance["ID"], cluster_instance["Type"], cluster_instance["State"], cluster_instance["Name"])

            if cluster_tag is None:
                print("Age:", cluster_instance['Age'])
                print("Region:", cluster_instance['Region'])
            first = False
        print()


def main():
    for region in get_all_regions():
        collect_instances(region)
    print_clusters()

sys.exit(main())
