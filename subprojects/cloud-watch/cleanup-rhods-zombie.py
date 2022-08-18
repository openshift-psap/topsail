#!/usr/bin/env python3

import datetime
import sys, time
from collections import defaultdict
import argparse

import boto3, botocore, botocore.errorfactory

PREFERED_REGIONS = ["us-east-1", "us-east-2", "us-west-2", "eu-central-1"]
now = datetime.datetime.now(datetime.timezone.utc)


hosted_zones = defaultdict(list)
hosted_zones_known = []
class State():
    def __init__(self):
        self.clusters = set()
        self.vpcs = defaultdict(list)
        self.vpc_peering_connections = defaultdict(list)
        self.dhcp_options = defaultdict(list)
        self.subnets = defaultdict(list)
        self.db_instances = defaultdict(list)
        self.db_snapshots = defaultdict(list)
        self.security_groups = defaultdict(list)


        self.all_instances = {}

        self.db_subnet_groups = defaultdict(list)

        self.ec2_client = None
        self.rds_client = None

state = None
args = None

DELETE_IDENTIFIERS = {
    "db_instances": "DBInstanceIdentifier",
    "db_snapshots": "DBSnapshotIdentifier",
    "db_subnet_groups": "DBSubnetGroupName",
    "security_groups": "GroupId",
    "subnets": "SubnetId",
    "vpcs": "VpcId",
    "vpc_peering_connections": "VpcPeeringConnectionId",
}

RESOURCE_ORDER = [
    "db_instances", "db_snapshots", "db_subnet_groups",
    "subnets", "security_groups", "vpc_peering_connections", "vpcs"
]

def delete_resource(client, res_type, instance_id, **kwargs):
    delete_meth = getattr(client, f"delete_{res_type}")

    if args.delete:
        print(f"Deleting {instance_id}...")

        return delete_meth(**kwargs)
    else:
        client_str = str(client)[1:].split()[0]
        print(f"DRY_RUN: {client_str}.delete_{res_type}({kwargs})")


def populate(aws_entries, tracking_dict, key):
    print(f"Collecting {key} ...")
    count = 0
    for entry in aws_entries:
        if "TagList" in entry and "Tags" not in entry:
            entry["Tags"] = entry["TagList"]

        if not entry.get("Tags"):
            entry["Tags"] = [dict(Key="empty", Value=True)]

        for tag in entry.get("Tags", []):
            if tag["Key"].startswith("kubernetes.io/cluster/"):
                cluster_id = tag["Key"].rpartition("/")[-1]
            elif tag["Key"] == "integreatly.org/clusterID":
                cluster_id = tag["Value"]
            elif tag["Key"] == "empty" and tag["Value"]:
                cluster_id = f"{entry[key]}--tags-missing"
            else:
                continue

            if args.ci_prefix and not cluster_id.startswith(args.ci_prefix):
                continue

            count += 1
            state.clusters.add(cluster_id)
            tracking_dict[cluster_id].append(entry[key])
            print(f"- {entry[key]} ({cluster_id})")
            state.all_instances[entry[key]] = entry
            break

    if count:
        print(f"Found {count} {key}.")


def wait_database_deletions():
    db_ids = []

    for cluster, db_instance_ids in state.db_instances.copy().items():
        for db_instance_id in db_instance_ids:
            db_ids.append(db_instance_id)

    while db_ids:
        db_id = db_ids[-1]

        try:
            instances = state.rds_client.describe_db_instances(DBInstanceIdentifier=db_id)

            if instances["DBInstances"]:
                if instances["DBInstances"][0]["DBInstanceStatus"] == "available":
                    print(f"WARNING: DB {db_id} not marked for deletion ...")
                else:
                    print(f"Waiting for {db_id} to be deleted ...")
                time.sleep(10)
                continue

            # db doesn't exit
        except state.rds_client.exceptions.DBInstanceNotFoundFault:
            pass # db doesn't exist

        db_ids.remove(db_id)
        print(f"DB {db_id} deleted, {len(db_ids)} to go ...")

def populate_hosted_zones(state):
    if hosted_zones: return
    count = 0
    print("Collecting hosted zones ...")
    zones = state.r53_client.list_hosted_zones()["HostedZones"]
    for zone in zones:
        zone_id = zone["Id"].split("/")[2]

        tags = state.r53_client.list_tags_for_resource(ResourceId=zone_id, ResourceType="hostedzone")["ResourceTagSet"]["Tags"]
        for tag in tags:
            if tag["Key"].startswith("kubernetes.io/cluster/"):
                cluster_id = tag["Key"].rpartition("/")[-1]
            else:
                continue

            if args.ci_prefix and not cluster_id.startswith(args.ci_prefix):
                continue

            count += 1
            hosted_zones[cluster_id] = zone["Name"]
            break

    print(f"Found {count} zones with Cluster IDs")

def process_region(region):
    global state

    state = State()

    my_config = botocore.config.Config(region_name=region)
    state.ec2_client = boto3.client("ec2", config=my_config)
    state.rds_client = boto3.client('rds', config=my_config)
    state.r53_client = boto3.client("route53", config=my_config)

    populate(state.ec2_client.describe_vpcs()["Vpcs"], state.vpcs, "VpcId")
    populate(state.ec2_client.describe_vpc_peering_connections()["VpcPeeringConnections"], state.vpc_peering_connections, "VpcPeeringConnectionId")
    populate(state.ec2_client.describe_security_groups()["SecurityGroups"], state.security_groups, "GroupId")
    populate(state.ec2_client.describe_subnets()['Subnets'], state.subnets, "SubnetId")

    populate(state.rds_client.describe_db_instances()['DBInstances'], state.db_instances, "DBInstanceIdentifier")

    populate(state.rds_client.describe_db_snapshots()['DBSnapshots'], state.db_snapshots, "DBSnapshotIdentifier")
    populate_hosted_zones(state)

    subnet_ids = dict()
    for cluster, cluster_subnets in state.subnets.items():
        for subnet in cluster_subnets:
            subnet_ids[subnet] = cluster

    for subnet_group in state.rds_client.describe_db_subnet_groups()['DBSubnetGroups']:
        for subnet in subnet_group["Subnets"]:
            subnet_id = subnet["SubnetIdentifier"]
            if subnet_id not in subnet_ids:
                continue
            cluster = subnet_ids[subnet_id]
            name = subnet_group["DBSubnetGroupName"]
            state.db_subnet_groups[cluster].append(name)

            state.all_instances[name] = subnet
            break

    print()
    for cluster in state.clusters.copy():
        cluster_filter = [
            {
                'Name': f'tag:kubernetes.io/cluster/{cluster}',
                'Values': ['owned']
            }
        ]
        instances = state.ec2_client.describe_instances(Filters=cluster_filter)

        if not instances["Reservations"]:
            continue

        instance_count = 0
        launch_time = now
        for resa in instances["Reservations"]:
            launch_time = min([resa["Instances"][0]["LaunchTime"], launch_time])
            instance_count += 1

        age_hr = (now - launch_time).total_seconds() / 60 / 60

        hosted_zone = None
        if cluster in hosted_zones:
            hosted_zone = hosted_zones[cluster]
            hosted_zones_known.append(hosted_zone)

        cluster_name = hosted_zone or cluster

        ignore = False
        if args.ci_prefix:
            if not cluster_name.startswith(args.ci_prefix):
                print(f"Ignore cluster {cluster_name} (not starting with '{args.ci_prefix}' CI prefix).")
                ignore = True
            elif args.ci_delete_older_than and age_hr < args.ci_delete_older_than:
                print(f"Ignore cluster {cluster_name} (age={age_hr:.1f} hours,"
                      f" not older than {args.ci_delete_older_than} hours).")
                ignore = True
            else:
                print(f"Cleanup cluster {cluster_name} (age={age_hr:.1f} hours,"
                      f" older than {args.ci_delete_older_than} hours).")
        else:
            print(f"Ignore cluster {cluster_name}: has {instance_count} ec2 instances"
                  f" (running for {age_hr:.1f} hours).")
            ignore = True

        if ignore:
            state.clusters.remove(cluster)
            continue

        instance_ids = []
        for resa in instances["Reservations"]:
            instance = resa["Instances"][0]
            instance_ids.append(instance["InstanceId"])

        msg = f"Terminating the cluster instances ... ({', '.join(instance_ids)})"
        if not args.delete:
            print("DRY_RUN:", msg)
            continue

        print(msg)
        state.ec2_client.terminate_instances(InstanceIds=instance_ids)


    for cluster in state.clusters:
        print()
        print(cluster)
        print("="*len(cluster))

        for what in RESOURCE_ORDER:

            instance_ids = getattr(state, what)[cluster]
            if not instance_ids: continue
            print()
            print("\t", what)
            print("\t", "-" * len(what))
            for instance_id in instance_ids:
                print("\t", f"{instance_id}")
    print()
    for what in RESOURCE_ORDER:
        for cluster in state.clusters:
            instance_ids = getattr(state, what)[cluster]
            if not instance_ids: continue

            for instance_id in instance_ids:
                res_type = str(what)[:-1]

                client = state.rds_client if what.startswith("db_") else state.ec2_client

                kwargs = {}
                kwargs[DELETE_IDENTIFIERS[what]] = instance_id
                if what == "db_instances":
                    kwargs["SkipFinalSnapshot"] = True
                    kwargs["DeleteAutomatedBackups"] = True

                do_delete = True
                if what == "db_instances":
                    if state.all_instances[instance_id]["DBInstanceStatus"] == "deleting":
                        print(f"{instance_id} already under deletion...")
                        do_delete = False
                    else:
                        if args.delete:
                            print(f"Removing {instance_id} deletion protection")
                            state.rds_client.modify_db_instance(DBInstanceIdentifier=instance_id, DeletionProtection=False)
                        else:
                            print(f"DRY_RUN: Remove {instance_id} deletion protection")

                elif what == "vpc_peering_connections":
                    if state.all_instances[instance_id]["Status"]["Code"] == "deleted":
                        print(f"{instance_id} already under deletion...")
                        do_delete = False

                if not do_delete: continue
                try:
                    delete_resource(client, res_type, instance_id, **kwargs)
                except Exception as e:
                    print(e)


            if what == "db_instances" and args.delete:
                wait_database_deletions()

            print()

def get_all_regions():
    if args.all_regions:
        return [region['RegionName'] for region in client_ec2.describe_regions()['Regions']]
    elif args.regions:
        return args.regions
    else:
        return PREFERED_REGIONS


def main():
    global args
    parser = argparse.ArgumentParser(description='Cleaning up of RHODS-related zombie AWS resources.')
    parser.add_argument('--delete', action='store_true', help='Perform the deletion of the zombie resources', default=False)
    parser.add_argument('--all-regions', action='store_true', help='Go through all the AWS regions', default=False)
    parser.add_argument('--regions', help='Go through the specified AWS regions', type=str, nargs='*')
    parser.add_argument('--ci-prefix', help='Cluster name prefix to identify CI-generated clusters', type=str)
    parser.add_argument('--ci-delete-older-than', help='Mark CI clusters older than this age (in hours) for deletion', type=int)

    args = parser.parse_args()

    if args.delete and not args.ci_delete_older_than:
        print("ERROR: refusing to run in delete mode without 'ci-delete-older-than' flag.")
        return 1

    for region in get_all_regions():
        print()
        print(f"### Region {region}")

        process_region(region)

    first_unknown_zone = True
    for cluster, zone in hosted_zones.items():
        if zone in hosted_zones_known: continue
        if first_unknown_zone:
            first_unknown_zone = False
            print("Zones unknown:")

        print("-", cluster, zone)

    if first_unknown_zone:
        print("No unknown cluster Hosted Zone detected.")

if __name__ == "__main__":
    sys.exit(main())
