#! /usr/bin/env python3

import pathlib
import shutil
import sys
import functools
import subprocess
import os
import logging
logging.getLogger().setLevel(logging.INFO)

import fire

TESTING_COMMON_DIR = pathlib.Path(__file__).absolute().parent
TESTING_UTILS_DIR = TESTING_COMMON_DIR.parent / "utils"
TESTING_PIPELINES_DIR = pathlib.Path(__file__).absolute().parent.parent / "pipelines"

sys.path.append(str(TESTING_COMMON_DIR.parent))
from common import env, config, run

matbench_config = None # will be set in init()
matbench_workload = None # will be set in init()
workload_storage_dir = None # will be set in init()



def init():
    global matbench_config, matbench_workload, workload_storage_dir

    env.init()
    config_file = os.environ.get("CI_ARTIFACTS_FROM_CONFIG_FILE")
    if not config_file:
        raise RuntimeError("CI_ARTIFACTS_FROM_CONFIG_FILE must be set. Please source your `configure.sh` before running this file.")

    config.init(pathlib.Path(config_file).parent)

    if config.ci_artifacts.get_config("PR_POSITIONAL_ARG_0", "").endswith("-plot"):
        pr_arg_1 = config.ci_artifacts.get_config("PR_POSITIONAL_ARG_1", "")
        if not pr_arg_1:
            raise ValueError("PR_POSITIONAL_ARG_1 should have been set ...")

        config.ci_artifacts.set_config("matbench.preset", pr_arg_1)


    matbench_workload =  config.ci_artifacts.get_config("matbench.workload")

    os.environ["MATBENCH_WORKLOAD"] = matbench_workload
    os.environ["MATBENCH_SIMPLE_STORE_IGNORE_EXIT_CODE"] = "true" if config.ci_artifacts.get_config("matbench.ignore_exit_code") else "false"

    workload_storage_dir = TESTING_COMMON_DIR.parent.parent / "visualizations" / matbench_workload

    if config.ci_artifacts.get_config("PR_POSITIONAL_ARG_0", "").endswith("-plot"):
        config.ci_artifacts.set_config("matbench.preset", config.ci_artifacts.get_config("PR_POSITIONAL_ARG_1", None))

    matbench_preset = config.ci_artifacts.get_config("matbench.preset")
    if not matbench_preset:
        pass # no preset defined, nothing to do
    elif str(matbench_preset).startswith("https://"):
        config.ci_artifacts.set_config("matbench.download.url", matbench_preset)
    else:
        config.ci_artifacts.set_config("matbench.config_file", f"{matbench_preset}.yaml")
        config.ci_artifacts.set_config("matbench.download.url_file", workload_storage_dir / "data" / f"{matbench_preset}.yaml")

    matbench_config = config.Config(workload_storage_dir / "data" / config.ci_artifacts.get_config("matbench.config_file"))


def entrypoint(fct):
    @functools.wraps(fct)
    def wrapper(*args, **kwargs):
        if matbench_config is None:
            init()
        fct(*args, **kwargs)

    return wrapper


@entrypoint
def prepare_matbench():

    run.run(f"""
    WORKLOAD_RUN_DIR="{TESTING_COMMON_DIR}/../../subprojects/matrix-benchmarking/workloads/{matbench_workload}"

    rm -f "$WORKLOAD_RUN_DIR"
    ln -s "{workload_storage_dir}" "$WORKLOAD_RUN_DIR"

    pip install --quiet --requirement "{TESTING_COMMON_DIR}/../../subprojects/matrix-benchmarking/requirements.txt"
    pip install --quiet --requirement "{workload_storage_dir}/requirements.txt"
    """)

    PROMETHEUS_VERSION = "2.36.0"
    os.environ["PATH"] += ":/tmp/prometheus"
    run.run(f"""
    if which prometheus 2>/dev/null; then
       echo "Prometheus already available."
       exit 0
    fi
    cd /tmp
    wget --quiet "https://github.com/prometheus/prometheus/releases/download/v{PROMETHEUS_VERSION}/prometheus-{PROMETHEUS_VERSION}.linux-amd64.tar.gz" -O/tmp/prometheus.tar.gz
    tar xf "/tmp/prometheus.tar.gz" -C /tmp
    mkdir -p /tmp/prometheus/bin
    ln -sf "/tmp/prometheus-{PROMETHEUS_VERSION}.linux-amd64/prometheus" /tmp/prometheus/bin
    cp "/tmp/prometheus-{PROMETHEUS_VERSION}.linux-amd64/prometheus.yml" /tmp/
    """)

@entrypoint
def generate_visualizations():
    if not os.environ.get("MATBENCH_RESULTS_DIRNAME"):
        raise ValueError("MATBENCH_RESULTS_DIRNAME should have been set ...")

    visualizations = matbench_config.get_config("visualize")
    plotting_failed = False
    for idx in range(len(visualizations)):
        generate_visualization(idx)

    if plotting_failed:
        raise RuntimeError("Som of visualization failed")


def generate_visualization(idx):
    generate_list = matbench_config.get_config(f"visualize[{idx}].generate")
    if not generate_list:
        raise ValueError(f"Couldn't get the configuration #{idx} ...")

    generate_url = "stats=" + "&stats=".join(generate_list)

    os.environ["MATBENCH_RHODS_PIPELINES_CONFIG"] = config.ci_artifacts.get_config("matbench.config_file")
    os.environ["MATBENCH_RHODS_PIPELINES_CONFIG_ID"] = matbench_config.get_config(f"visualize[{idx}].id")

    if (prom_cfg := pathlib.Path("/tmp/prometheus.yml")).exists():
        shutil.copyfile(prom_cfg, "./prometheus.yml")

    if run.run(f"PATH=$PATH:/tmp/prometheus/bin matbench parse |& tee > {env.ARTIFACT_DIR}/_matbench_parse.log", check=False).returncode != 0:
        raise RuntimeError("Failed to parse the results ...")

    error = False

    if config.ci_artifacts.get_config("matbench.generate_lts", False):
        if run.run(f"matbench parse --output_lts {env.ARTIFACT_DIR}/lts_payload.json |& tee > {env.ARTIFACT_DIR}/_matbench_generate_lts.log", check=False).returncode != 0:
            logging.warning("An error happened while generating the LTS payload ...")
            error = True

        if run.run(f"matbench export_lts_schema --file {env.ARTIFACT_DIR}/lts_payload.schema.json |& tee > {env.ARTIFACT_DIR}/_matbench_generate_lts_schema.log", check=False).returncode != 0:
            logging.warning("An error happened while generating the LTS payload schema...")
            error = True
    else:
        logging.info("matbench.generate_lts not enabled, skipping LTS payload&schema generation.")

    if config.ci_artifacts.get_config("matbench.download.save_to_artifacts"):
        shutil.copytree(os.environ["MATBENCH_RESULTS_DIRNAME"], env.ARTIFACT_DIR)

    filters = matbench_config.get_config(f"visualize[{idx}]").get("filters", [None])
    for filters_to_apply in filters:
        if not filters_to_apply:
            filters_to_apply = ""

        os.environ["MATBENCH_FILTERS"] = filters_to_apply

        dest_dir = env.ARTIFACT_DIR / filters_to_apply
        dest_dir.mkdir(parents=True, exist_ok=True)

        log_file = dest_dir / "_matbench_visualize.log"

        if run.run(f"matbench visualize --generate='{generate_url}' |& tee > {log_file}",
                check=False, cwd=dest_dir).returncode != 0:
            logging.warning("An error happened while generating the visualization ...")
            error = True

        with open(log_file) as log_f:
            for line in log_f.readlines():
                if not line.startswith("ERROR"):
                    continue
                error = True
                with open(env.ARTIFACT_DIR / "FAILURE", "a") as fail_f:
                    print(line, end="", file=fail_f)
                print(line.strip())

        del os.environ["MATBENCH_FILTERS"]
        run.run(f"""
        cd
        mkdir -p {dest_dir}/figures_{{png,html}}
        mv {dest_dir}/fig_*.png "{dest_dir}/figures_png" 2>/dev/null || true
        mv {dest_dir}/fig_*.html "{dest_dir}/figures_html" 2>/dev/null || true
        """)

    if error:
        logging.error("An error happened during the report generation ...")
        sys.exit(1)


@entrypoint
def generate_from_dir(results_dirname):
    os.environ["MATBENCH_RESULTS_DIRNAME"] = results_dirname

    generate_visualizations()


def download():
    url = config.ci_artifacts.get_config("matbench.download.url")
    url_file = config.ci_artifacts.get_config("matbench.download.url_file")
    if url:
        os.environ["MATBENCH_URL"] = url
        with open(env.ARTIFACT_DIR / "source_url", "w") as f:
            print(url, file=f)

    elif url_file:
        shutil.copyfile(url_file, env.ARTIFACT_DIR / "source_url")
    else:
        raise ValueError("matbench.download.url or matbench.download.url_file must be specified")

    os.environ["MATBENCH_MODE"] = config.ci_artifacts.get_config("matbench.download.mode")

    if not os.environ.get("MATBENCH_RESULTS_DIRNAME"):
        raise ValueError("internal error: MATBENCH_RESULTS_DIRNAME should have been set :/")

    run.run(f"matbench download --do-download |& tee > {env.ARTIFACT_DIR}/_matbench_download.log")


@entrypoint
def download_and_generate_visualizations():
    prepare_matbench()
    os.environ["MATBENCH_RESULTS_DIRNAME"] = "/tmp/matrix_benchmarking_results"

    download()

    generate_visualizations()


class Visualize:
    """
    Commands for launching the Pipeline Perf & Scale tests
    """

    def __init__(self):
        self.prepare_matbench = prepare_matbench
        self.generate_visualizations = generate_visualizations
        self.generate_visualizations_from_dir = generate_from_dir
        self.download_and_generate_visualizations = download_and_generate_visualizations


def main():
    # Print help rather than opening a pager
    fire.core.Display = lambda lines, out: print(*lines, file=out)

    fire.Fire(Visualize())


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{e.cmd}' failed --> {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print() # empty line after ^C
        logging.error(f"Interrupted.")
        sys.exit(1)
