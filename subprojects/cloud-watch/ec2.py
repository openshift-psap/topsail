import sys
import datetime
import boto3
import botocore.config
from collections import defaultdict
import argparse

IGNORE_LESS_THAN_DAYS = 0
PREFERED_REGIONS = ["us-east-2", "us-east-1", "us-west-2", "eu-central-1"]
now = datetime.datetime.now(datetime.timezone.utc)

client_ec2 = boto3.client('ec2')
resource_ec2 = boto3.resource('ec2')
r53_client = boto3.client("route53")

clusters = defaultdict(list)
cluster_zones = {}
clusters_to_list = []

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

args = None

def collect_instances(region=None):
    print(f"Looking at the {region} region ...")

    if region is None:
        regional_resource_ec2 = resource_ec2
    else:
        my_config = botocore.config.Config(region_name=region)
        regional_resource_ec2 = boto3.resource("ec2", config=my_config)

    zones = r53_client.list_hosted_zones()["HostedZones"]
    for zone in zones:
        zone_id = zone["Id"].split("/")[2]

        tags = r53_client.list_tags_for_resource(ResourceId=zone_id, ResourceType="hostedzone")["ResourceTagSet"]["Tags"]
        for tag in tags:
            if tag["Key"].startswith("kubernetes.io/cluster/"):
                cluster_id = tag["Key"].rpartition("/")[-1]
            else: continue

            cluster_zones[cluster_id] = zone["Name"].strip(".")
            break


    instance_count = 0
    instances_stopped = 0
    instances_ignored_too_young = 0
    instances_ignored_from_list = 0
    instances_ignored_terminated = 0
    for instance in regional_resource_ec2.instances.all():
        age = (now - instance.launch_time).days
        age_hr = (now - instance.launch_time).seconds / 60 / 60
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
            "ID": instance.id.split("/")[-1],
            "Type": instance.instance_type,
            "State": instance.state["Name"],
            "Age": f"{age} days",
            "Region": region,
            "Name": "<not defined>",
        }

        if age < 1:
            if age_hr < 1:
                info["Age"] += f" ({age_hr*60:.0f} minutes)"
            else:
                info["Age"] += f" ({age_hr:.1f} hours)"

        for tag in instance.tags or {}:
            if tag["Key"] == "Name":
                info["Name"] = tag["Value"]
            if tag["Value"] == "owned":
                info["Cluster ID"] = tag["Key"]

        if info["Name"] in IGNORE_NODES:
            instances_ignored_from_list += 1
            continue

        if info.get("Cluster ID", "") in IGNORE_CLUSTERS:
            instances_ignored_from_list += 1
            continue

        if args.ci_prefix:
            if not info["Name"].startswith(args.ci_prefix):
                continue

            if args.ci_list_older_than and age_hr < args.ci_list_older_than:
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
    if args.all_regions:
        return [region['RegionName'] for region in client_ec2.describe_regions()['Regions']]
    elif args.regions:
        return args.regions
    else:
        return PREFERED_REGIONS


def print_clusters():
    for cluster_tag in reversed(sorted(map(str, clusters))):
        if cluster_tag == "None":
            cluster_name = "Not part of a cluster"
            cluster_tag = None
            hosted_zone = ""
        else:
            cluster_name = cluster_tag.rpartition("/")[-1]
            hosted_zone = cluster_zones.get(cluster_name, "")

        print(hosted_zone or cluster_name)
        print("="*len(hosted_zone or cluster_name))
        first = True
        for cluster_instance in clusters[cluster_tag]:

            if cluster_tag is not None:
                cluster_instance = dict(cluster_instance) # make a copy of the dict
                cluster_instance.pop('Cluster ID')
                cluster_instance['Name'] = cluster_instance['Name'].replace(f"{cluster_tag}-", "")
                if first:
                    if cluster_tag != "None":
                        print("Cluster:", cluster_instance['Region'], cluster_name)
                    print("Age:", cluster_instance['Age'])

                    if args.ci_prefix and args.ci_list_older_than:
                        if args.ci_list_file:
                            with open(args.ci_list_file, "a") as out_f:
                                print(f"{cluster_instance['Region']} {cluster_name}", file=out_f)

                            print(f"WARNING: CI cluster {cluster_name} ({cluster_instance['Region']}) marked for deletion.")
                        else:
                            print(f"WARNING: CI cluster {cluster_name} ({cluster_instance['Region']}) is too old.")

            print(cluster_instance["ID"], cluster_instance["Type"], cluster_instance["State"], cluster_instance["Name"])

            if cluster_tag is None:
                print("Age:", cluster_instance['Age'])
                print("Region:", cluster_instance['Region'])

            first = False
        print()


def main():
    global args
    parser = argparse.ArgumentParser(description='Cleaning up of RHODS-related zombie AWS resources.')
    parser.add_argument('--all-regions', action='store_true', help='Go through all the AWS regions', default=False)
    parser.add_argument('--regions', help='Go through the specified AWS regions', type=str, nargs='*')
    parser.add_argument('--ci-prefix', help='Cluster name prefix to identify CI-generated clusters', type=str)
    parser.add_argument('--ci-list-older-than', help='Mark CI clusters older than this age (in hours) for deletion', type=int)
    parser.add_argument('--ci-list-file', help='Name of a file where the cluster to delete will be listed. Format: One "<region> <cluster_id>" per line.', type=str)
    args = parser.parse_args()

    for region in get_all_regions():
        print(f"Region: {region}")
        collect_instances(region)

    print_clusters()

sys.exit(main())
