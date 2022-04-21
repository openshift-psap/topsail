#! /usr/bin/env python

import sys

import common

def create_snapshot(cluster_name, instance, zone):
    volume = common.get_instance_root_volume(instance)

    print(f"Volume Id: {volume.id}")

    ts = common.human_ts()

    snapshot = volume.create_snapshot(
        Description=f'Snapshot of cluster {cluster_name}.',
        TagSpecifications=[{
            'ResourceType': 'snapshot',
            'Tags': [
                {'Key': 'Name', 'Value': f'{cluster_name}-{ts}'},
                {'Key': f'kubernetes.io/cluster/{cluster_name}', 'Value': 'owned'},
            ]
        }],)

    print(f"Snapshot Id: {snapshot.id}")

    resp = common.client_ec2.enable_fast_snapshot_restores(
        AvailabilityZones=[zone,],
        SourceSnapshotIds=[snapshot.id,],
    )

    if not "Successful" in resp.keys():
        raise RuntimeError(f"aws.ec2.enable_fast_snapshot_restores failed ... {resp}")

    print(f"Snapshot added to availability zone {zone}.")

    return snapshot


def main():
    common.configure()

    machine_props = common.get_machine_props()
    print()

    snapshot = common.get_cluster_snapshot(*machine_props)
    created = False

    if snapshot is None:
        if "--delete" in sys.argv:
            print("ERROR: no snapshot to delete ...")
            return 1

        snapshot = create_snapshot(*machine_props)
        created = True

    awaited = False
    if "--wait" in sys.argv:
        awaited = True
        common.await_snapshot(snapshot)
    elif created:
        print("Not waiting for the snapshot creation. Pass '--wait' to wait for its completion.")

    if created:
        return

    if "--delete" not in sys.argv:
        if not awaited:
            print(f"WARNING: a snapshot ({snapshot.id}) already exists.")
            print("Pass '--delete' to delete it.")
            if snapshot.progress != "100%":
                print(f"Pass '--wait' to wait for its completion. ({snapshot.progress})")
        return

    print(f"Deleting the snapshot {snapshot.id} ...")
    snapshot.delete()
    print("Done.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
