
#! /bin/bash

# configure the ImageRegistry to use an emptyDir as storage backend

oc patch configs.imageregistry.operator.openshift.io cluster --type merge --patch '{"spec":{"storage":{"emptyDir":{}}}}'

if ! oc get crd/localvolumes.local.storage.openshift.io -oname; then
    echo "Install the Local Storage Operator from OperatorHub ..."
    exit 1
fi

cat <<EOF | oc apply -f-
apiVersion: "local.storage.openshift.io/v1"
kind: "LocalVolume"
metadata:
  name: "local-disk"
  namespace: "openshift-local-storage"
spec:
  nodeSelector:
    nodeSelectorTerms:
    - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values:
          - dgxa100
  storageClassDevices:
    - storageClassName: local-sc-dgx
      volumeMode: Filesystem
      fsType: xfs
      devicePaths:
        - /dev/nvme2n1
EOF

cat <<EOF | oc apply -f-
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: benchmarking-coco-dataset
  namespace: default
spec:
  storageClassName: local-sc-dgx
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 80Gi
EOF
