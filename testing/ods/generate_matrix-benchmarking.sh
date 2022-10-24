#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -x

THIS_DIR="$(cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd)"

ARTIFACT_DIR=${ARTIFACT_DIR:-/tmp/ci-artifacts_$(date +%Y%m%d)}

MATBENCH_WORKLOAD=rhods-notebooks-ux
MATBENCH_GENERATE_LIST=notebooks_scale_test
MATBENCH_GENERATE_FILTERS=
MATBENCH_MODE='prefer_cache'
MATBENCH_DATA_URL=

# if not empty, copy the results downloaded by `matbench download` into the artifacts directory
SAVE_MATBENCH_DOWNLOAD=

if [[ "${ARTIFACT_DIR:-}" ]] && [[ -f "${ARTIFACT_DIR}/variable_overrides" ]]; then
    source "${ARTIFACT_DIR}/variable_overrides"
fi

if [[ "${PR_POSITIONAL_ARGS:-}" == "reference" ]]; then
    MATBENCH_GENERATE_LIST=reference_comparison
    MATBENCH_GENERATE_FILTERS=reference_comparison
    PR_POSITIONAL_ARGS=subprojects/matrix-benchmarking-workloads/rhods-notebooks-ux/data/references.url
    PR_POSITIONAL_ARG_0=$PR_POSITIONAL_ARGS
fi

if [[ "${PR_POSITIONAL_ARGS:-}" == "notebook_perf_comparison" ]]; then
    MATBENCH_GENERATE_LIST=notebook_perf_comparison
    PR_POSITIONAL_ARGS=subprojects/matrix-benchmarking-workloads/rhods-notebooks-ux/data/notebook_perf_comparison.url
    PR_POSITIONAL_ARG_0=$PR_POSITIONAL_ARGS
fi

export MATBENCH_MODE
export MATBENCH_WORKLOAD

WORKLOAD_STORAGE_DIR="$THIS_DIR/../../subprojects/matrix-benchmarking-workloads/$MATBENCH_WORKLOAD"

if [[ -z "${MATBENCH_WORKLOAD:-}" ]]; then
    echo "ERROR: $0 expects 'MATBENCH_WORKLOAD' to be set ..."
    exit 1
fi

generate_matbench::prepare_matrix_benchmarking() {
    WORKLOAD_RUN_DIR="$THIS_DIR/../../subprojects/matrix-benchmarking/workloads/$MATBENCH_WORKLOAD"

    rm -f "$WORKLOAD_RUN_DIR"
    ln -s "$WORKLOAD_STORAGE_DIR" "$WORKLOAD_RUN_DIR"

    pip install --quiet --requirement "$THIS_DIR/../../subprojects/matrix-benchmarking/requirements.txt"
    pip install --quiet --requirement "$WORKLOAD_STORAGE_DIR/requirements.txt"
}

_get_data_from_pr() {
    MATBENCH_DATA_URL=${PR_POSITIONAL_ARGS:-$MATBENCH_DATA_URL}
    if [[ -z "${MATBENCH_DATA_URL}" ]]; then
        echo "ERROR: _get_data_from_pr expects PR_POSITIONAL_ARGS or MATBENCH_DATA_URL to be set ..."
        exit 1
    fi

    if [[ -z "$MATBENCH_RESULTS_DIRNAME" ]]; then
        echo "ERROR: _get_data_from_pr expects MATBENCH_RESULTS_DIRNAME to be set ..."
    fi

    _download_data_from_url "$MATBENCH_DATA_URL"
}

_download_data_from_url() {
    url=$1
    shift

    if [[ "$url" == "https"* ]]; then
        echo "$url" > "$ARTIFACT_DIR/source_url"
        matbench download --do-download --url "$url" |& tee >"$ARTIFACT_DIR/_matbench_download.log"
    else
        cp "$HOME/$url" "$ARTIFACT_DIR/source_url"
        matbench download --do-download --url-file "$HOME/$url" |& tee > "$ARTIFACT_DIR/_matbench_download.log"
    fi
}

generate_matbench::get_prometheus() {
    export PATH=$PATH:/tmp/bin
    if which prometheus 2>/dev/null; then
       echo "Prometheus already available."
       return
    fi
    PROMETHEUS_VERSION=2.36.0
    cd /tmp
    wget --quiet "https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz" -O/tmp/prometheus.tar.gz
    tar xf "/tmp/prometheus.tar.gz" -C /tmp
    mkdir -p /tmp/bin
    ln -sf "/tmp/prometheus-${PROMETHEUS_VERSION}.linux-amd64/prometheus" /tmp/bin
    cp "/tmp/prometheus-${PROMETHEUS_VERSION}.linux-amd64/prometheus.yml" /tmp/
}

generate_matbench::generate_plots() {
    if [[ -z "${MATBENCH_RESULTS_DIRNAME:-}" ]]; then
        echo "ERROR: expected MATBENCH_RESULTS_DIRNAME to be set ..."
    fi

    echo "Generating from ${MATBENCH_GENERATE_LIST} ..."
    stats_content="$(cat "$WORKLOAD_STORAGE_DIR/data/${MATBENCH_GENERATE_LIST}.plots" | cut -d'#' -f1 | grep -v '^$')"

    NO_FILTER="no-filter"
    if [[ "$MATBENCH_GENERATE_FILTERS" ]]; then
        filters_content="$(cat "$WORKLOAD_STORAGE_DIR/data/${MATBENCH_GENERATE_FILTERS}.filters" | cut -d'#' -f1 | (grep -v '^$' || true))"
    else
        filters_content="$NO_FILTER"
    fi

    generate_url="stats=$(echo -n "$stats_content" | tr '\n' '&' | sed 's/&/&stats=/g')"

    cp -f /tmp/prometheus.yml "." || true
    if ! matbench parse |& tee > "$ARTIFACT_DIR/_matbench_parse.log"; then
        echo "An error happened during the parsing of the results (or no results were available), aborting."
        return 1
    fi

    if [[ "$SAVE_MATBENCH_DOWNLOAD" ]]; then
        cp -rv "$MATBENCH_RESULTS_DIRNAME" "$ARTIFACT_DIR"
    fi

    retcode=0
    for filters in $filters_content; do
        if [[ "$filters" == "$NO_FILTER" ]]; then
            filters=""
        fi
        mkdir -p "$ARTIFACT_DIR/$filters"
        cd "$ARTIFACT_DIR/$filters"

        VISU_LOG_FILE="$ARTIFACT_DIR/$filters/_matbench_visualize.log"

        export MATBENCH_FILTERS="$filters"
        if ! matbench visualize --generate="$generate_url" |& tee > "$VISU_LOG_FILE"; then
            echo "Visualization generation failed :("
            retcode=1
        fi
        if grep "^ERROR" "$VISU_LOG_FILE"; then
            echo "An error happened during the report generation, aborting."
            grep "^ERROR" "$VISU_LOG_FILE" > "$ARTIFACT_DIR"/FAILURE
            retcode=1
        fi
        unset MATBENCH_FILTERS

        mkdir -p figures_{png,html}
        mv fig_*.png "figures_png" 2>/dev/null || true
        mv fig_*.html "figures_html" 2>/dev/null || true
    done

    cd "$ARTIFACT_DIR"
    return $retcode
}

action=${1:-}

if [[ "$action" == "prepare_matbench" ]]; then
    generate_matbench::get_prometheus
    generate_matbench::prepare_matrix_benchmarking

elif [[ "$action" == "generate_plots" ]]; then
    generate_matbench::generate_plots

elif [[ "$action" == "from_dir" ]]; then
    dir=${2:-}

    if [[ -z "$dir" ]]; then
        echo "ERROR: no directory provided in 'from_dir' mode ..."
        exit 1
    fi
    export MATBENCH_RESULTS_DIRNAME="$dir"

    generate_matbench::get_prometheus
    generate_matbench::prepare_matrix_benchmarking

    generate_matbench::generate_plots

elif [[ "$action" == "from_pr_args" || "$JOB_NAME_SAFE" == "nb-plot" ]]; then
    generate_matbench::get_prometheus
    generate_matbench::prepare_matrix_benchmarking

    export MATBENCH_RESULTS_DIRNAME="/tmp/matrix_benchmarking_results"
    _get_data_from_pr

    generate_matbench::generate_plots

else
    echo "ERROR: unknown action='$action' (JOB_NAME_SAFE='$JOB_NAME_SAFE')"
    exit 1
fi
