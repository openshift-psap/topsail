#! /usr/bin/env bash

# from https://github.com/openshift/release/blob/1007481fb9945e159a05e14f23e659d41110995b/ci-operator/step-registry/openshift/e2e/cert-rotation/prepare-for-shutdown/openshift-e2e-cert-rotation-prepare-for-shutdown-commands.sh#L52-L78

mapfile -d ' ' -t control_nodes < <( oc get nodes --selector='node-role.kubernetes.io/master' --template='{{ range $index, $_ := .items }}{{ range .status.addresses }}{{ if (eq .type "InternalIP") }}{{ if $index }} {{end }}{{ .address }}{{ end }}{{ end }}{{ end }}' )
mapfile -d ' ' -t compute_nodes < <( oc get nodes --selector='!node-role.kubernetes.io/master' --template='{{ range $index, $_ := .items }}{{ range .status.addresses }}{{ if (eq .type "InternalIP") }}{{ if $index }} {{end }}{{ .address }}{{ end }}{{ end }}{{ end }}' )

fields=( kubernetes.io/kube-apiserver-client-kubelet kubernetes.io/kubelet-serving )
for field in ${fields[@]}; do
    echo "Approving ${field} CSRs at $(date)"

    (( required_csrs=${#control_nodes[@]} + ${#compute_nodes[@]} ))
    (( required_csrs=${#control_nodes[@]} + ${#compute_nodes[@]} ))
    approved_csrs=0
    attempts=0
    max_attempts=6
    while (( required_csrs >= approved_csrs )); do
        echo -n '.'
        mapfile -d ' ' -t csrs < <(oc get csr --field-selector=spec.signerName=${field} --no-headers | grep Pending | cut -f1 -d" ")
        if [[ ${#csrs[@]} -gt 0 ]]; then
            echo ""
            oc adm certificate approve ${csrs} && attempts=0 && (( approved_csrs=approved_csrs+${#csrs[@]} ))
        else
            (( attempts++ ))
        fi
        if (( attempts > max_attempts )); then
            break
        fi
        sleep 10s
    done
    echo ""
done
echo "Finished CSR approval at $(date)"
