OpenShift SNO Snapshot/Rollback with AWS
========================================

This WIP sub-project aims at providing a snapshot/rollback capability
to a single-node OpenShift cluster running on AWS.

Snapshotting
------------

```
./snapshot.py

    Creates the snapshot of the current state of the SNO node, if no
    snapshot already exists.

./snapshot.py --wait

    Creates or awaits for the completion of the current AWS
    snapshot. This takes several minutes to complete, but 1/ the
    cluster is available during the snapshot creation and 2/ any
    changes performed after the snapshot creation time will not be
    included in the snapshot.

./snapshot.py --delete

    Deletes the AWS snapshot associated with this cluster, so that a
    new one can be created.
```

*Open questions*:

- Should the node be turned off before triggering the snapshot?

*Todo*:

- Include a human-readable timestamp in the snapshot name and printed
  in (instead of the snapshot ID)
- Delete all the OpenShift/Kubernetes objects backed by AWS objects
  (extra machines, routes, auto-scaling, ...)
  - These objects will be deleted during the cluster tear down anyway,
    but better avoid letting them dangling if we can.

Rolling Back
------------

```
./rollback.py

    Rolls back the cluster to the snapshot time.
    Fails if there is exising snapshot.
    Fails if the snapshot isn't completed yet.
    Waits for the completion of the AWS snapshot rollback and the
    reloading of RHCOS/OpenShift.


./rollback.py --wait-snapshot

   Wait for the completion of the AWS snapshot if it is not ready.

./rollback.py --only-wait-openshift

  Only wait for OpenShift to respond properly.
```
