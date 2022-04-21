#! /usr/bin/env python

import sys, time

import common

def rollback(snapshot, cluster_name, instance, zone):
    volume = common.get_instance_root_volume(instance)

    ts = common.human_ts()

    print(f"Old Volume Id: {volume.id}")

    print("Triggering the rollback!")
    resp = common.client_ec2.create_replace_root_volume_task(
        InstanceId=instance.id,
        SnapshotId=snapshot.id,
        TagSpecifications=[
            {
                'ResourceType': 'volume',
                'Tags': [
                    {'Key': 'Name', 'Value': f'{cluster_name}-restored-at-{ts}'},
                    {'Key': f'kubernetes.io/cluster/{cluster_name}', 'Value': 'owned'},
                ]
            },
            {
                'ResourceType': 'replace-root-volume-task',
                'Tags': [
                    # replace-root-volume-task objects cannot be
                    # deleted, so do not use the 'owned' value below,
                    # otherwise `openshift-install destroy cluster`
                    # will loop forever as it detects resources owned
                    # by the cluster.
                    # https://github.com/aws/aws-cli/issues/6650
                    {'Key': f'kubernetes.io/cluster/{cluster_name}', 'Value': 'createdby'},
                    {'Key': f'costless-resource', 'Value': 'true'},
                ]
            },
        ]
    )

    replace_id = resp["ReplaceRootVolumeTask"]["ReplaceRootVolumeTaskId"]
    print(f"Replacement Id: {replace_id}")
    state = resp["ReplaceRootVolumeTask"]["TaskState"]
    prev = state
    print(f"Waiting for the completion of the replacement ... (state={state})")
    while state in ('pending', 'in-progress'):
        time.sleep(10)

        resp = common.client_ec2.describe_replace_root_volume_tasks(
            ReplaceRootVolumeTaskIds=[replace_id]
        )
        state = resp["ReplaceRootVolumeTasks"][0]["TaskState"]
        if prev != state:
            print(state)
            prev = state

    if state != "succeeded":
        print("Rollback failed ...")
        return 1

    print(f"Cluster rolled back to snapshot {snapshot.id}")

    volume.delete()
    print(f"Old volume {volume.id} deleted.")

def has_ongoing_rollback(cluster_name, instance, zone):
    first = True

    resp = common.client_ec2.describe_replace_root_volume_tasks(
        Filters=[{
            'Name': f'tag:kubernetes.io/cluster/{cluster_name}',
            'Values': ['createdby']
        }]
    )

    ongoing = False
    for task in resp["ReplaceRootVolumeTasks"]:
        state = task["TaskState"]
        if state in ('pending', 'in-progress'):
            ongoing = True
            if first:
                first = False
                print("Found ongoing an task:")
            print(task)

    return ongoing

def main():
    common.configure()
    machine_props = common.get_machine_props()
    print()

    if "--only-wait-openshift" in sys.argv:
        common.wait_openshift()
        return

    snapshot = common.get_cluster_snapshot(*machine_props)

    if snapshot is None:
        print("ERROR: no snapshot to restore ...")
        return 1

    if snapshot.progress != "100%":
        if "--wait-snapshot" not in sys.argv:
            print("ERROR: cannot restore the snapshot before it completed.")
            print(f"Pass '--wait-snapshot' to wait for its completion. ({snapshot.progress})")
            return 1

        common.await_snapshot(snapshot)


    if has_ongoing_rollback(*machine_props):
        print("ERROR: cannot trigger multiple rollbacks at the same time ...")
        return 1

    rollback(snapshot, *machine_props)

    common.wait_openshift()

    return

if __name__ == "__main__":
    sys.exit(main())
