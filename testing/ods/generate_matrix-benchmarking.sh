#! /bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -x

TESTING_ODS_DIR="$(cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd)"

source "$TESTING_ODS_DIR/configure.sh"
bash "$TESTING_ODS_DIR/configure_overrides.sh"

ARTIFACT_DIR=${ARTIFACT_DIR:-/tmp/ci-artifacts_$(date +%Y%m%d)}

set_config_from_pr_arg 0 "matbench.preset"

matbench_preset=$(get_config matbench.preset)
if [[ "$matbench_preset" == "notebooks_scale_tests_comparison" ]]; then
    set_config matbench.generate.list_file "$matbench_preset"
    set_config matbench.generate.filters_file "$matbench_preset"
    set_config matbench.download.url_file "subprojects/matrix-benchmarking-workloads/rhods-notebooks-ux/data/${matbench_preset}.url"
elif [[ "$matbench_preset" == "notebook_perf_comparison" ]]; then
    set_config matbench.generate.list_file "$matbench_preset"
    set_config matbench.download.url_file "subprojects/matrix-benchmarking-workloads/rhods-notebooks-ux/data/${matbench_preset}.url"
elif [[ "$matbench_preset" == "https://"* ]]; then
    set_config matbench.download.url "$matbench_preset"
fi

export MATBENCH_WORKLOAD=$(get_config matbench.workload)


WORKLOAD_STORAGE_DIR="$TESTING_ODS_DIR/../../subprojects/matrix-benchmarking-workloads/$MATBENCH_WORKLOAD"

generate_matbench::prepare_matrix_benchmarking() {
    WORKLOAD_RUN_DIR="$TESTING_ODS_DIR/../../subprojects/matrix-benchmarking/workloads/$MATBENCH_WORKLOAD"

    rm -f "$WORKLOAD_RUN_DIR"
    ln -s "$WORKLOAD_STORAGE_DIR" "$WORKLOAD_RUN_DIR"

    pip install --quiet --requirement "$TESTING_ODS_DIR/../../subprojects/matrix-benchmarking/requirements.txt"
    pip install --quiet --requirement "$WORKLOAD_STORAGE_DIR/requirements.txt"
}

_get_data_from_pr() {
    if [[ -z "$MATBENCH_RESULTS_DIRNAME" ]]; then
        echo "ERROR: _get_data_from_pr expects MATBENCH_RESULTS_DIRNAME to be set ..."
    fi

    MATBENCH_URL=$(get_config matbench.download.url)
    MATBENCH_URL_FILE=$(get_config matbench.download.url_file)

    if [[ "$MATBENCH_URL" != null ]]; then
        export MATBENCH_URL

        echo "$MATBENCH_URL" > "$ARTIFACT_DIR/source_url"
    elif [[ "$MATBENCH_URL_FILE" != null ]]; then
        export MATBENCH_URL_FILE

        cp "$HOME/$MATBENCH_URL_FILE" "$ARTIFACT_DIR/source_url"
    else
        _error "matbench.download.url or matbench.download.url_file must be specified"
    fi
    export MATBENCH_MODE=$(get_config matbench.download.mode)

    matbench download --do-download |& tee > "$ARTIFACT_DIR/_matbench_download.log"
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

    generate_list=$(get_config matbench.generate.list_file)
    echo "Generating from ${generate_list} ..."
    stats_content="$(cat "$WORKLOAD_STORAGE_DIR/data/${generate_list}.plots" | cut -d'#' -f1 | grep -v '^$')"

    NO_FILTER="no-filter"
    filters_file=$(get_config matbench.generate.filters_file)
    if [[ "$filters_file" != null ]]; then
        filters_content="$(cat "$WORKLOAD_STORAGE_DIR/data/${filters_file}.filters" | cut -d'#' -f1 | (grep -v '^$' || true))"
    else
        filters_content="$NO_FILTER"
    fi

    generate_url="stats=$(echo -n "$stats_content" | tr '\n' '&' | sed 's/&/&stats=/g')"

    cp -f /tmp/prometheus.yml "." || true
    if ! matbench parse |& tee > "$ARTIFACT_DIR/_matbench_parse.log"; then
        echo "An error happened during the parsing of the results (or no results were available), aborting."
        return 1
    fi

    if test_config matbench.download.save_to_artifacts; then
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

elif [[ "$action" == "from_pr_args" ]]; then
    generate_matbench::get_prometheus
    generate_matbench::prepare_matrix_benchmarking

    export MATBENCH_RESULTS_DIRNAME="/tmp/matrix_benchmarking_results"
    _get_data_from_pr

    generate_matbench::generate_plots

else
    echo "ERROR: unknown action='$action' (JOB_NAME_SAFE='$JOB_NAME_SAFE')"
    exit 1
fi
