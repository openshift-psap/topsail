#!/usr/bin/env python3

import datetime
import sys, time
from collections import defaultdict
import argparse

import boto3, botocore

s3_client = boto3.client('s3')
s3_resource = boto3.resource('s3')

clusters = defaultdict(list)


parser = argparse.ArgumentParser(description='Cleaning up of RHODS-related Velero AWS S3 buckets.')
parser.add_argument('--delete', action='store_true', help='Perform the deletion of the zombie resources', default=False)

args = parser.parse_args()

print("Querying the buckets ...")
for bucket in s3_client.list_buckets()["Buckets"]:
    try:
        tagset = s3_client.get_bucket_tagging(Bucket=bucket["Name"])["TagSet"]
    except botocore.exceptions.ClientError:
        # no tags
        continue

    for tag in tagset:
        if tag["Key"] != "velero.io/infrastructureName": continue # ignore

        clusters[tag["Value"]].append(bucket["Name"])
        print(".", end="", flush=True)

print()

for cluster_name, buckets in clusters.items():
    print(cluster_name)
    print("-"*len(cluster_name))
    for bucket in buckets:
        print(f"- {bucket}")
        if not args.delete: continue

        s3_bucket = s3_resource.Bucket(bucket)

        # Deleting objects
        for s3_object in s3_bucket.objects.all():
            s3_object.delete()
            print("  +", s3_object.key)

        # Deleting objects versions if S3 versioning enabled
        for s3_object_ver in s3_bucket.object_versions.all():
            s3_object_ver.delete()
            print("  +", s3_object.key)

        print("  * S3 Bucket cleaned up.")

        s3_bucket.delete()
        print("  * Deleted.")

    print()
