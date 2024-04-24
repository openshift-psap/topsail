#!/bin/bash

# kpouget: imported from
# https://github.com/openshift/release/blob/8de7ecc42af9af62aa473b7f0468b07d92d5f74f/ci-operator/step-registry/gather/extra/gather-extra-commands.sh

if [ "${PERFLAB_CI:-}" == true ]; then
	LOG_FILE=$ARTIFACT_DIR/gather_extra.log
	echo "Running in the PerfLab CI, mutting the gather-extra std output. See $LOG_FILE for details."
	exec &>"$LOG_FILE"
fi

function queue() {
	local TARGET="${1}"
	shift
	local LIVE
	LIVE="$(jobs | wc -l)"
	while [[ "${LIVE}" -ge 45 ]]; do
		sleep 1
		LIVE="$(jobs | wc -l)"
	done
	echo "${@}"
	if [[ -n "${FILTER:-}" ]]; then
		"${@}" | "${FILTER}" >"${TARGET}" &
	else
		"${@}" >"${TARGET}" &
	fi
}
if ! oc whoami 2>/dev/null >/dev/null; then
	if test ! -f "${KUBECONFIG}"; then
		echo "No kubeconfig, so no point in gathering extra artifacts."
		exit 0
	else
		echo "Cannot access OpenShift server ..."
		oc whoami
		exit 1
	fi
fi
OC="oc --request-timeout=5s"

echo "Gathering artifacts ..."
mkdir -p ${ARTIFACT_DIR}/pods ${ARTIFACT_DIR}/nodes ${ARTIFACT_DIR}/metrics ${ARTIFACT_DIR}/bootstrap ${ARTIFACT_DIR}/network ${ARTIFACT_DIR}/oc_cmds ${ARTIFACT_DIR}/internal

$OC get nodes -o jsonpath --template '{range .items[*]}{.metadata.name}{"\n"}{end}' >/tmp/nodes
$OC get nodes -o jsonpath --template '{range .items[*]}{.metadata.name}{"\n"}{end}' -lnode-role.kubernetes.io/master >/tmp/control_plan_nodes
$OC get pods --all-namespaces --template '{{ range .items }}{{ $name := .metadata.name }}{{ $ns := .metadata.namespace }}{{ range .spec.containers }}-n {{ $ns }} {{ $name }} -c {{ .name }}{{ "\n" }}{{ end }}{{ range .spec.initContainers }}-n {{ $ns }} {{ $name }} -c {{ .name }}{{ "\n" }}{{ end }}{{ end }}' >${ARTIFACT_DIR}/internal/containers

queue ${ARTIFACT_DIR}/config-resources.json $OC get apiserver.config.openshift.io authentication.config.openshift.io build.config.openshift.io console.config.openshift.io dns.config.openshift.io featuregate.config.openshift.io image.config.openshift.io infrastructure.config.openshift.io ingress.config.openshift.io network.config.openshift.io oauth.config.openshift.io project.config.openshift.io scheduler.config.openshift.io -o json
queue ${ARTIFACT_DIR}/apiservices.json $OC get apiservices -o json
queue ${ARTIFACT_DIR}/oc_cmds/apiservices $OC get apiservices
queue ${ARTIFACT_DIR}/clusteroperators.json $OC get clusteroperators -o json
queue ${ARTIFACT_DIR}/oc_cmds/clusteroperators $OC get clusteroperators
queue ${ARTIFACT_DIR}/clusterversion.json $OC get clusterversion -o json
queue ${ARTIFACT_DIR}/oc_cmds/clusterversion $OC get clusterversion
queue ${ARTIFACT_DIR}/configmaps.json $OC get configmaps --all-namespaces -o json
queue ${ARTIFACT_DIR}/oc_cmds/configmaps $OC get configmaps --all-namespaces
queue ${ARTIFACT_DIR}/credentialsrequests.json $OC get credentialsrequests --all-namespaces -o json
queue ${ARTIFACT_DIR}/oc_cmds/credentialsrequests $OC get credentialsrequests --all-namespaces
queue ${ARTIFACT_DIR}/csr.json $OC get csr -o json
queue ${ARTIFACT_DIR}/endpoints.json $OC get endpoints --all-namespaces -o json
queue ${ARTIFACT_DIR}/oc_cmds/endpoints $OC get endpoints --all-namespaces
FILTER=gzip queue ${ARTIFACT_DIR}/deployments.json.gz $OC get deployments --all-namespaces -o json
queue ${ARTIFACT_DIR}/oc_cmds/deployments $OC get deployments --all-namespaces -o wide
FILTER=gzip queue ${ARTIFACT_DIR}/daemonsets.json.gz $OC get daemonsets --all-namespaces -o json
queue ${ARTIFACT_DIR}/oc_cmds/daemonsets $OC get daemonsets --all-namespaces -o wide
queue ${ARTIFACT_DIR}/events.json $OC get events --all-namespaces -o json
queue ${ARTIFACT_DIR}/oc_cmds/events $OC get events --all-namespaces
queue ${ARTIFACT_DIR}/kubeapiserver.json $OC get kubeapiserver -o json
queue ${ARTIFACT_DIR}/oc_cmds/kubeapiserver $OC get kubeapiserver
queue ${ARTIFACT_DIR}/kubecontrollermanager.json $OC get kubecontrollermanager -o json
queue ${ARTIFACT_DIR}/oc_cmds/kubecontrollermanager $OC get kubecontrollermanager
queue ${ARTIFACT_DIR}/machineconfigpools.json $OC get machineconfigpools -o json
queue ${ARTIFACT_DIR}/oc_cmds/machineconfigpools $OC get machineconfigpools
queue ${ARTIFACT_DIR}/machineconfigs.json $OC get machineconfigs -o json
queue ${ARTIFACT_DIR}/oc_cmds/machineconfigs $OC get machineconfigs
queue ${ARTIFACT_DIR}/machinesets.json $OC get machinesets -A -o json
queue ${ARTIFACT_DIR}/oc_cmds/machinesets $OC get machinesets -A
queue ${ARTIFACT_DIR}/machines.json $OC get machines -A -o json
queue ${ARTIFACT_DIR}/oc_cmds/machines $OC get machines -A -o wide
queue ${ARTIFACT_DIR}/namespaces.json $OC get namespaces -o json
queue ${ARTIFACT_DIR}/oc_cmds/namespaces $OC get namespaces
queue ${ARTIFACT_DIR}/nodes.json $OC get nodes -o json
queue ${ARTIFACT_DIR}/oc_cmds/nodes $OC get nodes -o wide
queue ${ARTIFACT_DIR}/openshiftapiserver.json $OC get openshiftapiserver -o json
queue ${ARTIFACT_DIR}/oc_cmds/openshiftapiserver $OC get openshiftapiserver
queue ${ARTIFACT_DIR}/pods.json $OC get pods --all-namespaces -o json
queue ${ARTIFACT_DIR}/oc_cmds/jobs $OC get jobs --all-namespaces -o wide
queue ${ARTIFACT_DIR}/jobs.json $OC get jobs --all-namespaces -o json
queue ${ARTIFACT_DIR}/oc_cmds/pods $OC get pods --all-namespaces -o wide
queue ${ARTIFACT_DIR}/persistentvolumes.json $OC get persistentvolumes --all-namespaces -o json
queue ${ARTIFACT_DIR}/oc_cmds/persistentvolumes $OC get persistentvolumes --all-namespaces -o wide
queue ${ARTIFACT_DIR}/persistentvolumeclaims.json $OC get persistentvolumeclaims --all-namespaces -o json
queue ${ARTIFACT_DIR}/oc_cmds/persistentvolumeclaims $OC get persistentvolumeclaims --all-namespaces -o wide
FILTER=gzip queue ${ARTIFACT_DIR}/replicasets.json.gz $OC get replicasets --all-namespaces -o json
queue ${ARTIFACT_DIR}/oc_cmds/replicasets $OC get replicasets --all-namespaces -o wide
queue ${ARTIFACT_DIR}/rolebindings.json $OC get rolebindings --all-namespaces -o json
queue ${ARTIFACT_DIR}/oc_cmds/rolebindings $OC get rolebindings --all-namespaces
queue ${ARTIFACT_DIR}/roles.json $OC get roles --all-namespaces -o json
queue ${ARTIFACT_DIR}/oc_cmds/roles $OC get roles --all-namespaces
queue ${ARTIFACT_DIR}/services.json $OC get services --all-namespaces -o json
queue ${ARTIFACT_DIR}/oc_cmds/services $OC get services --all-namespaces
FILTER=gzip queue ${ARTIFACT_DIR}/statefulsets.json.gz $OC get statefulsets --all-namespaces -o json
queue ${ARTIFACT_DIR}/oc_cmds/statefulsets $OC get statefulsets --all-namespaces
queue ${ARTIFACT_DIR}/routes.json $OC get routes --all-namespaces -o json
queue ${ARTIFACT_DIR}/oc_cmds/routes $OC get routes --all-namespaces
queue ${ARTIFACT_DIR}/subscriptions.json $OC get subscriptions --all-namespaces -o json
queue ${ARTIFACT_DIR}/oc_cmds/subscriptions $OC get subscriptions --all-namespaces
queue ${ARTIFACT_DIR}/clusterserviceversions.json $OC get clusterserviceversions --all-namespaces -o json
queue ${ARTIFACT_DIR}/oc_cmds/clusterserviceversions $OC get clusterserviceversions --all-namespaces
queue ${ARTIFACT_DIR}/packagemanifests.json $OC get packagemanifests --all-namespaces -o json
queue ${ARTIFACT_DIR}/oc_cmds/packagemanifests $OC get packagemanifests --all-namespaces

queue ${ARTIFACT_DIR}/infrastructure.yaml $OC get infrastructure/cluster

# gather nodes first in parallel since they may contain the most relevant debugging info
platform_type=$(oc get infrastructure/cluster -ojsonpath={.status.platformStatus.type})
if [[ "$platform_type" == "BareMetal" ]]; then
	echo "WARNING: gathering of node logs disabled on bare-metal platforms"
else
	while IFS= read -r i; do
		mkdir -p ${ARTIFACT_DIR}/nodes/$i
		queue ${ARTIFACT_DIR}/nodes/$i/heap oc --insecure-skip-tls-verify get --request-timeout=20s --raw /api/v1/nodes/$i/proxy/debug/pprof/heap
		FILTER=gzip queue ${ARTIFACT_DIR}/nodes/$i/journal.gz oc --insecure-skip-tls-verify adm node-logs $i --unify=false
		FILTER=gzip queue ${ARTIFACT_DIR}/nodes/$i/journal-previous.gz oc --insecure-skip-tls-verify adm node-logs $i --unify=false --boot=-1
		FILTER=gzip queue ${ARTIFACT_DIR}/nodes/$i/audit.gz oc --insecure-skip-tls-verify adm node-logs $i --unify=false --path=audit/audit.log
	done </tmp/nodes
fi

# gather nodes first in parallel since they may contain the most relevant debugging info
while IFS= read -r i; do
	mkdir -p ${ARTIFACT_DIR}/nodes/$i
	FILTER=gzip queue ${ARTIFACT_DIR}/nodes/$i/kube-apiserver.audit.gz oc --insecure-skip-tls-verify adm node-logs $i --unify=false --path=kube-apiserver/audit.log
done </tmp/control_plan_nodes

echo "INFO: gathering the audit logs for each master"
paths=(openshift-apiserver kube-apiserver oauth-apiserver etcd)
for path in "${paths[@]}"; do
	if [[ "$platform_type" == "BareMetal" ]]; then
		echo "WARNING: gathering of audit logs on the master disabled on baremetal platforms."
		continue
	fi
	output_dir="${ARTIFACT_DIR}/audit_logs/$path"
	mkdir -p "$output_dir"

	# Skip downloading of .terminating and .lock files.
	oc adm node-logs --role=master --path="$path" |
		grep -v ".terminating" |
		grep -v ".lock" |
		tee "${output_dir}.audit_logs_listing"

	# The ${output_dir}.audit_logs_listing file contains lines with the node and filename
	# separated by a space.
	while IFS= read -r item; do
		node=$(echo $item | cut -d ' ' -f 1)
		fname=$(echo $item | cut -d ' ' -f 2)
		echo "INFO: Queueing download/gzip of ${path}/${fname} from ${node}"
		echo "INFO:   gziping to ${output_dir}/${node}-${fname}.gz"
		FILTER=gzip queue ${output_dir}/${node}-${fname}.gz oc --insecure-skip-tls-verify adm node-logs ${node} --path=${path}/${fname}
	done <${output_dir}.audit_logs_listing
done

while IFS= read -r i; do
	file="$(echo "$i" | cut -d ' ' -f 2,3,5 | tr -s ' ' '_')"
	FILTER=gzip queue ${ARTIFACT_DIR}/pods/${file}.log.gz oc --insecure-skip-tls-verify logs --request-timeout=20s $i
	FILTER=gzip queue ${ARTIFACT_DIR}/pods/${file}_previous.log.gz oc --insecure-skip-tls-verify logs --request-timeout=20s -p $i
done <${ARTIFACT_DIR}/internal/containers

# Snapshot the prometheus data from the replica that has the oldest
# PVC. If persistent storage isn't enabled, it uses the last
# prometheus instances by default to catch issues that occur when the
# first prometheus pod upgrades.
if [[ -n "$(oc --insecure-skip-tls-verify --request-timeout=20s get pvc -n openshift-monitoring -l app.kubernetes.io/name=prometheus --ignore-not-found)" ]]; then
	pvc="$(oc --insecure-skip-tls-verify --request-timeout=20s get pvc -n openshift-monitoring -l app.kubernetes.io/name=prometheus --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[0].metadata.name}')"
	prometheus="${pvc##prometheus-data-}"
else
	prometheus="$(oc --insecure-skip-tls-verify --request-timeout=20s get pods -n openshift-monitoring -l app.kubernetes.io/name=prometheus --sort-by=.metadata.creationTimestamp --ignore-not-found -o jsonpath='{.items[0].metadata.name}')"
fi
if [[ -n "${prometheus}" ]]; then
	echo "Snapshotting prometheus from ${prometheus} (may take 15s) ..."
	queue ${ARTIFACT_DIR}/metrics/prometheus.tar.gz oc --insecure-skip-tls-verify exec -n openshift-monitoring "${prometheus}" -- tar cvzf - -C /prometheus .

	cat >>${SHARED_DIR}/custom-links.txt <<-EOF
		<script>
		let prom = document.createElement('a');
		prom.href="https://promecieus.dptools.openshift.org/?search="+document.referrer;
		prom.title="Creates a new prometheus deployment with data from this job run.";
		prom.innerHTML="PromeCIeus";
		prom.target="_blank";
		document.getElementById("wrapper").append(prom);
		</script>
	EOF

	FILTER=gzip queue ${ARTIFACT_DIR}/metrics/prometheus-target-metadata.json.gz oc --insecure-skip-tls-verify exec -n openshift-monitoring "${prometheus}" -- /bin/bash -c "curl -G http://localhost:9090/api/v1/targets/metadata --data-urlencode 'match_target={instance!=\"\"}'"
	FILTER=gzip queue ${ARTIFACT_DIR}/metrics/prometheus-config.json.gz oc --insecure-skip-tls-verify exec -n openshift-monitoring "${prometheus}" -- /bin/bash -c "curl -G http://localhost:9090/api/v1/status/config"
	queue ${ARTIFACT_DIR}/metrics/prometheus-tsdb-status.json oc --insecure-skip-tls-verify exec -n openshift-monitoring "${prometheus}" -- /bin/bash -c "curl -G http://localhost:9090/api/v1/status/tsdb"
	queue ${ARTIFACT_DIR}/metrics/prometheus-runtimeinfo.json oc --insecure-skip-tls-verify exec -n openshift-monitoring "${prometheus}" -- /bin/bash -c "curl -G http://localhost:9090/api/v1/status/runtimeinfo"
	queue ${ARTIFACT_DIR}/metrics/prometheus-targets.json oc --insecure-skip-tls-verify exec -n openshift-monitoring "${prometheus}" -- /bin/bash -c "curl -G http://localhost:9090/api/v1/targets"
else
	echo "Unable to find a Prometheus pod to snapshot."
fi

wait

echo "Extracting the gz files ..."

if [ "${PERFLAB_CI:-}" == true ]; then
	echo "Running in the PerfLab CI, extracting the gz files."

	find "${ARTIFACT_DIR}" -name "*.gz" -exec gunzip {} \;
fi
