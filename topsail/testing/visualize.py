#! /usr/bin/env python

import pathlib
import shutil
import sys
import functools
import subprocess
import os
import logging
logging.getLogger().setLevel(logging.INFO)

import fire

TOPSAIL_TESTING_DIR = pathlib.Path(__file__).absolute().parent
TOPSAIL_DIR = TOPSAIL_TESTING_DIR.parent.parent

from topsail.testing import env, config, run

matbench_config = None # will be set in init()
matbench_workload = None # will be set in init()
workload_storage_dir = None # will be set in init()


def init(allow_no_config_file=False):
    global matbench_config, matbench_workload, workload_storage_dir

    env.init()
    config_file = os.environ.get("CI_ARTIFACTS_FROM_CONFIG_FILE")
    if not config_file and not allow_no_config_file:
        raise RuntimeError("CI_ARTIFACTS_FROM_CONFIG_FILE must be set. Please source your `configure.sh` before running this file.")

    if not config_file:
        logging.info("Running without CI_ARTIFACTS_FROM_CONFIG_FILE, skipping most of the initialization")
        return

    config.init(pathlib.Path(config_file).parent)

    if config.ci_artifacts.get_config("PR_POSITIONAL_ARG_0", "").endswith("-plot"):
        pr_arg_1 = config.ci_artifacts.get_config("PR_POSITIONAL_ARG_1", "")
        if not pr_arg_1:
            raise ValueError("PR_POSITIONAL_ARG_1 should have been set ...")

        config.ci_artifacts.set_config("matbench.preset", pr_arg_1, dump_command_args=False)

    matbench_workload = config.ci_artifacts.get_config("matbench.workload")

    workload_storage_dir = pathlib.Path(matbench_workload.replace(".", "/"))

    if config.ci_artifacts.get_config("PR_POSITIONAL_ARG_0", "").endswith("-plot"):
        config.ci_artifacts.set_config("matbench.preset", config.ci_artifacts.get_config("PR_POSITIONAL_ARG_1", None), dump_command_args=False)

    matbench_preset = config.ci_artifacts.get_config("matbench.preset")
    if not matbench_preset:
        pass # no preset defined, nothing to do
    elif str(matbench_preset).startswith("https://"):
        config.ci_artifacts.set_config("matbench.download.url", matbench_preset, dump_command_args=False)
    else:
        config.ci_artifacts.set_config("matbench.config_file", f"{matbench_preset}.yaml", dump_command_args=False)
        config.ci_artifacts.set_config("matbench.download.url_file", workload_storage_dir / "data" / f"{matbench_preset}.yaml", dump_command_args=False)

    matbench_config = config.Config(workload_storage_dir / "data" / config.ci_artifacts.get_config("matbench.config_file"))


def entrypoint(allow_no_config_file=False):
    def decorator(fct):
        @functools.wraps(fct)
        def wrapper(*args, **kwargs):
            init(allow_no_config_file)
            fct(*args, **kwargs)

        return wrapper
    return decorator


@entrypoint(allow_no_config_file=True)
def prepare_matbench():

    run.run(f"""
    pip install --quiet --requirement "{TOPSAIL_DIR}/subprojects/matrix-benchmarking/requirements.txt"
    """)


@entrypoint()
def generate_visualizations(results_dirname, generate_lts=None):
    visualizations = matbench_config.get_config("visualize")
    plotting_failed = False
    for idx in range(len(visualizations)):
        generate_visualization(results_dirname, idx, generate_lts=generate_lts)

    if plotting_failed:
        raise RuntimeError("Som of visualization failed")


def generate_visualization(results_dirname, idx, generate_lts=None):
    generate_list = matbench_config.get_config(f"visualize[{idx}].generate")
    if not generate_list:
        raise ValueError(f"Couldn't get the configuration #{idx} ...")

    generate_url = "stats=" + "&stats=".join(generate_list)

    common_args, common_env = get_common_matbench_args_env(results_dirname)

    parse_env = common_env.copy()
    mode = config.ci_artifacts.get_config("matbench.download.mode")
    if mode != "prefer_cache":
        logging.info(f"Download mode set to '{mode}', ignoring the parser cache.")
        parse_env["MATBENCH_STORE_IGNORE_CACHE"] = "y"

    parse_args = common_args.copy()
    parse_args["output-matrix"] = env.ARTIFACT_DIR / "internal_matrix.json"

    parse_args_str = " ".join(f"'--{k}={v}'" for k, v in parse_args.items())
    parse_env_str = "env " + " ".join(f"'{k}={v}'" for k, v in parse_env.items())

    if run.run(f"{parse_env_str} matbench parse {parse_args_str}  |& tee > {env.ARTIFACT_DIR}/_matbench_parse.log", check=False).returncode != 0:
        raise RuntimeError("Failed to parse the results ...")

    error = False
    lts_args = common_args.copy()
    lts_args["output-lts"] = env.ARTIFACT_DIR / "lts_payload.json"
    lts_args_str = " ".join(f"'--{k}={v}'" for k, v in lts_args.items())

    common_env_str = "env " + " ".join(f"'{k}={v}'" for k, v in common_env.items())

    do_generate_lts = generate_lts if generate_lts is not None \
        else config.ci_artifacts.get_config("matbench.lts.generate", None) \

    if do_generate_lts:
        if run.run(f"{common_env_str} matbench parse {lts_args_str} |& tee > {env.ARTIFACT_DIR}/_matbench_generate_lts.log", check=False).returncode != 0:
            logging.warning("An error happened while generating the LTS payload ...")
            error = True

        lts_schema_args = common_args.copy()
        lts_schema_args.pop("results_dirname")
        lts_schema_args["file"] = env.ARTIFACT_DIR / "lts_payload.schema.json"
        lts_schema_args_str = " ".join(f"'--{k}={v}'" for k, v in lts_schema_args.items())
        if run.run(f"matbench generate_lts_schema {lts_schema_args_str}  |& tee > {env.ARTIFACT_DIR}/_matbench_generate_lts_schema.log", check=False).returncode != 0:
            logging.warning("An error happened while generating the LTS payload schema...")
            error = True
    else:
        if generate_lts is not None:
            logging.info(f"'matbench.lts.generate' parameter is set to {generate_lts}, skipping LTS payload&schema generation.")
        else:
            logging.info("'matbench.lts.generate' not enabled, skipping LTS payload&schema generation.")

    if config.ci_artifacts.get_config("matbench.download.save_to_artifacts"):
        shutil.copytree(common_args["MATBENCH_RESULTS_DIRNAME"], env.ARTIFACT_DIR / "downloaded")


    filters = matbench_config.get_config(f"visualize[{idx}]").get("filters", [None])
    for filters_to_apply in filters:
        if not filters_to_apply:
            filters_to_apply = ""

        visu_args = common_args.copy()
        visu_args["filters"] = filters_to_apply
        visu_args["generate"] = generate_url
        visu_args_str = " ".join(f"'--{k}={v}'" for k, v in visu_args.items())

        dest_dir = env.ARTIFACT_DIR / filters_to_apply
        dest_dir.mkdir(parents=True, exist_ok=True)

        log_file = dest_dir / "_matbench_visualize.log"

        if run.run(f"{common_env_str} matbench visualize {visu_args_str} |& tee > {log_file}",
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

        run.run(f"""
        cd
        mkdir -p {dest_dir}/figures_{{png,html}}
        mv {dest_dir}/fig_*.png "{dest_dir}/figures_png" 2>/dev/null || true
        mv {dest_dir}/fig_*.html "{dest_dir}/figures_html" 2>/dev/null || true
        """)

    if error:
        msg = "An error happened during the report generation ..."
        logging.error(msg)
        raise RuntimeError(msg)


@entrypoint()
def generate_from_dir(results_dirname, generate_lts=None):
    logging.info(f"Generating the visualization from '{results_dirname}' ...")

    generate_visualizations(results_dirname, generate_lts=generate_lts)


def get_common_matbench_args_env(results_dirname):
    common_args = dict()
    common_args["results_dirname"] = results_dirname
    common_args["workload"] = config.ci_artifacts.get_config("matbench.workload")

    common_args["workload_base_dir"] = str(TOPSAIL_DIR)

    common_env = dict()
    common_env["MATBENCH_SIMPLE_STORE_IGNORE_EXIT_CODE"] = "true" if config.ci_artifacts.get_config("matbench.ignore_exit_code") else "false"

    return common_args, common_env


def download(results_dirname):
    url = config.ci_artifacts.get_config("matbench.download.url")
    url_file = config.ci_artifacts.get_config("matbench.download.url_file")

    if url:
        with open(env.ARTIFACT_DIR / "source_url", "w") as f:
            print(url, file=f)

    elif url_file:
        shutil.copyfile(url_file, env.ARTIFACT_DIR / "source_url")
    else:
        raise ValueError("matbench.download.url or matbench.download.url_file must be specified")

    common_args, common_env = get_common_matbench_args_env(results_dirname)

    download_args = common_args.copy()
    download_args |= dict(
        mode=config.ci_artifacts.get_config("matbench.download.mode"),
        do_download=True,
    )

    if url:
        download_args["url"] = url
    elif url_file:
        download_args["url_file"] = url_file

    download_args_str = " ".join(f"'--{k}={v}'" for k, v in download_args.items())
    common_env_str = "env " + " ".join(f"'{k}={v}'" for k, v in common_env.items())

    run.run(f"{common_env_str} matbench download {download_args_str} |& tee > {env.ARTIFACT_DIR}/_matbench_download.log")


@entrypoint()
def download_and_generate_visualizations(results_dirname="/tmp/matrix_benchmarking_results"):
    prepare_matbench()

    download(results_dirname)

    generate_visualizations(results_dirname)


class Visualize:
    """
    Commands for launching the visualization commands
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
