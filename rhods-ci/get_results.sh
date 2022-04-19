#! /bin/bash

oc get job/ods-ci -oyaml > results/job.yaml
oc get pods -oyaml > results/pods.yaml
oc get ev -oyaml > results/ev.yaml
