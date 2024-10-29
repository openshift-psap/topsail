import logging
import datetime, time

from projects.core.library import config, env, run

def dump_prometheus(prom_start_ts, namespace, testing_dir, delay=60):
    capture_prom = config.project.get_config("tests.capture_prom", True)
    if not capture_prom:
        logging.info("tests.capture_prom is disabled, skipping Prometheus DB dump")
        return

    if config.project.get_config("tests.dry_mode", False):
        logging.info("tests.dry_mode is enabled, skipping Prometheus DB dump")
        return

    if capture_prom == "with-queries":
        if config.project.get_config("tests.capture_prom_uwm", False):
            logging.error("tests.capture_prom_uwm not supported with capture Prom with queries")

        prom_end_ts = datetime.datetime.now()
        args = dict(
            duration_s = (prom_end_ts - prom_start_ts).total_seconds(),
            promquery_file = testing_dir / "metrics.txt",
            dest_dir = env.ARTIFACT_DIR / "metrics",
            namespace = namespace,
        )

        with env.NextArtifactDir("cluster__dump_prometheus_dbs"):
            run.run_toolbox("cluster", "query_prometheus_db", **args)
            with env.NextArtifactDir("cluster__dump_prometheus_db"):
                with open(env.ARTIFACT_DIR / "prometheus.tar.dummy", "w") as f:
                    print(f"""This file is a dummy.
Metrics have been queried from Prometheus and saved into {args['dest_dir']}.
Keep this file here, so that 'projects/fine_tuning/visualizations/fine_tuning_prom/store/parsers.py' things Prometheus metrics have been captured,
and it directly processes the cached files from the metrics directory.""", file=f)
                nodes = run.run("oc get nodes -ojson", capture_stdout=True)
                with open(env.ARTIFACT_DIR / "nodes.json", "w") as f:
                    print(nodes.stdout.strip(), file=f)

        return

    # prom_start_ts not used when during full prometheus dump.

    logging.info(f"Wait {delay}s for Prometheus to finish collecting data ...")
    time.sleep(delay)

    with run.Parallel("cluster__dump_prometheus_dbs") as parallel:
        parallel.delayed(run.run_toolbox, "cluster", "dump_prometheus_db", mute_stdout=True)
        if config.project.get_config("tests.capture_prom_uwm"):
            parallel.delayed(run.run_toolbox_from_config, "cluster", "dump_prometheus_db", suffix="uwm", artifact_dir_suffix="_uwm", mute_stdout=True)


def reset_prometheus(delay=60):
    capture_prom = config.project.get_config("tests.capture_prom", True)
    if not capture_prom:
        logging.info("tests.capture_prom is disabled, skipping Prometheus DB reset")
        return

    prom_start_ts = datetime.datetime.now()

    if capture_prom == "with-queries":
        return prom_start_ts

    if config.project.get_config("tests.dry_mode", False):
        logging.info("tests.dry_mode is enabled, skipping Prometheus DB reset")
        return

    with run.Parallel("cluster__reset_prometheus_dbs") as parallel:
        parallel.delayed(run.run_toolbox, "cluster", "reset_prometheus_db", mute_stdout=True)
        if config.project.get_config("tests.capture_prom_uwm", False):
            parallel.delayed(run.run_toolbox_from_config, "cluster", "reset_prometheus_db", suffix="uwm", artifact_dir_suffix="_uwm", mute_stdout=True)

    logging.info(f"Wait {delay}s for Prometheus to restart collecting data ...")
    time.sleep(delay)

    # at the moment, only used when capture_prom == "with-queries".
    # Returned for consistency.
    return prom_start_ts
