#! /bin/bash

MATBENCH_EXPE_NAME=rhods-ci
ARTIFACT_DIR=${ARTIFACT_DIR:-/tmp/ci-artifacts_$(date +%Y%m%d)}
MATBENCH_RESULTS_DIR="/tmp/matrix_benchmarking_results"

generate_matbench::get_matrix_benchmarking() {
    cd /tmp
    git clone https://github.com/openshift-psap/matrix-benchmarking --depth 1

    cd matrix-benchmarking/
    pip install --quiet --requirement requirements.txt

    cd matrix_benchmarking
    rm workloads/ -rf
    git clone https://github.com/kpouget/matrix-benchmarking-workloads -b rhods --depth 1 workloads

    cd workloads/rhods-ci/
    pip install --quiet --requirement requirements.txt

    mkdir -p /tmp/bin

    ln -s /tmp/matrix-benchmarking/bin/matbench /tmp/bin
}

_get_data_from_pr() {
    cluster_type=$1
    shift;
    results_dir=$1
    shift

    if [[ -z "${PULL_NUMBER:-}" ]]; then
        echo "ERROR: PULL_NUMBER not set :/"
        exit 1
    fi

    MATBENCH_URL_ANCHOR="matbench-data-url: "
    MATBENCH_BUILD_ANCHOR="matbench-data-build: "

    pr_body="$(curl -sSf "https://api.github.com/repos/openshift-psap/ci-artifacts/pulls/$PULL_NUMBER" | jq -r .body | tr -d '\r')"

    get_anchor_value() {
        anchor=$1
        shift || true
        default=${1:-}

        value=$(echo "$pr_body" | { grep "$anchor" || true;} | cut -b$(echo "$anchor" | wc -c)-)

        [[ "$value" ]] && echo "$value" || echo "$default"
    }

    matbench_url=$(get_anchor_value "$MATBENCH_URL_ANCHOR")

    if [[ -z "$matbench_url" ]]; then
        base_url="https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/origin-ci-test/pr-logs/pull/openshift-psap_ci-artifacts/$PULL_NUMBER/pull-ci-openshift-psap-ci-artifacts-master-ods-jh-on-${cluster_type}"

        build=$(get_anchor_value "$MATBENCH_BUILD_ANCHOR")
        if [[ -z "$build" ]]; then
            build=$(curl --silent -Ssf "${base_url}/latest-build.txt")
        fi

        matbench_url="${base_url}/${build}/artifacts/jh-on-${cluster_type}/test/artifacts/"
    fi

    echo "$matbench_url" > "${ARTIFACT_DIR}/source_url"

    _download_data_from_url "$results_dir" "$matbench_url"
}

_download_data_from_url() {
    results_dir=$1
    shift
    url=$1
    shift

    if [[ "${url: -1}" != "/" ]]; then
        url="${url}/"
    fi

    mkdir -p "$results_dir"

    dl_dir=$(echo "$url" | cut -d/ -f4-)
    (cd "$results_dir"; wget --recursive --no-host-directories --no-parent --execute robots=off --quiet \
                             --cut-dirs=$(echo "${dl_dir}" | tr -cd / | wc -c) \
                             "$url")
}

generate_matbench::get_prometheus() {
    PROMETHEUS_VERSION=2.36.0
    cd /tmp
    wget --quiet "https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz" -O/tmp/prometheus.tar.gz
    tar xf "/tmp/prometheus.tar.gz" -C /tmp
    mkdir -p /tmp/bin
    ln -s "/tmp/prometheus-${PROMETHEUS_VERSION}.linux-amd64/prometheus" /tmp/bin
    ln -s "/tmp/prometheus-${PROMETHEUS_VERSION}.linux-amd64/prometheus.yml" /tmp/
}

generate_matbench::generate_plots() {
    workload_dir=/tmp/matrix-benchmarking/workloads/rhods-ci

    ln -s /tmp/prometheus.yml "$workload_dir"

    export PATH="/tmp/bin:$PATH"
    python3 --version

    cat > "$workload_dir/.env" <<EOF
MATBENCH_RESULTS_DIRNAME=$MATBENCH_RESULTS_DIR
MATBENCH_FILTERS=expe=$MATBENCH_EXPE_NAME
EOF

    cat "$workload_dir/.env"

    _matbench() {
        (cd  "$workload_dir"; matbench "$@")
    }


    stats_content="$(cat "$workload_dir/data/ci-artifacts.plots")"

    echo "$stats_content"

    generate_url="stats=$(echo -n "$stats_content" | tr '\n' '&' | sed 's/&/&stats=/g')"

    _matbench parse
    _matbench visualize --generate="$generate_url" || true

    mkdir "$ARTIFACT_DIR"/{png,html}

    mv *.png "$ARTIFACT_DIR/png"
    mv *.html "$ARTIFACT_DIR/html"
}


if [[ "$JOB_NAME_SAFE" == "plot-jh-on-"* ]]; then
    set -o errexit
    set -o pipefail
    set -o nounset
    set -x

    cluster_type=$1

    results_dir="$MATBENCH_RESULTS_DIR/$MATBENCH_EXPE_NAME"
    mkdir -p "$results_dir"

    _get_data_from_pr "$cluster_type" "$results_dir"

    generate_matbench::get_prometheus
    generate_matbench::get_matrix_benchmarking

    generate_matbench::generate_plots
fi
