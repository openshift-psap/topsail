#! /usr/bin/env python

import fire
import sys, os
import yaml
import pathlib
import yaml, json
from collections import defaultdict
import datetime
import logging
logging.getLogger().setLevel(logging.INFO)

import subprocess

import jsonpath_ng

import k8s_quantity
import scheduler

import run, config, utils
import job as job_mod
import appwrapper as appwrapper_mod
import kueue as kueue_mod
import coscheduling as coscheduling_mod

def main(dry_run=True,
         namespace=None,
         job_template_name="sleeper",
         mode="job",

         pod_count=1,
         pod_runtime=30,
         pod_requests={"cpu": "1"},

         base_name="sched-test-",
         priority=10,

         count=30,
         timespan=0,
         distribution="poisson",
         visualize=True,

         kueue_queue="local-queue",
         ):
    """
    Generates workload for the MCAD load test

    Args:
      dry_run: if True (default), only prepares the resources. If False, instanciate them in the cluster
      namespace: namespace in which the workload should be instanciated
      job_template_name: name of the job template to use
      mode: mcad or kueue or job
      pod_count: number of Pods to create in each of the resource
      pod_runtime: run time parameter to pass to the Pod
      pod_requests: requests to pass to the Pod definition
      base_name: name prefix for the resources to create
      priority: priority to give to the resource

      count: number of resources to create
      timespan: number of minutes over which the AppWrappers should be created
      distribution: the distribution method to use to spread the resource creation over the requested timespan
      visualize: activate or deactive the visualization of the generator load distribution

      kueue_queue: name of the Kueue queue to use, in Kueue mode
    """

    if namespace is None:
        logging.info("Getting the current project name ...")

        namespace = run("oc project --short", capture_stdout=True).stdout.strip() \
            if not dry_run else "<DRY RUN>"

    logging.info(f"Using namespace '{namespace}' to deploy the workload.")


    job_mode = False
    kueue_mode = False
    mcad_mode = False
    if mode == "job":
        job_mode = True
        logging.info(f"Running in {mode} mode")
        kind_name = "Jobs"
    elif mode == "kueue":
        kueue_mode = True
        logging.info("Running in Kueue mode")
        kind_name = "Kueue Jobs"
    elif mode == "mcad":
        mcad_mode = True
        logging.info("Running in AppWrapper mode")
        kind_name = "AppWrappers Jobs"
    elif mode == "coscheduling":
        coscheduling_mode = True
        logging.info("Running in Coscheduling mode")
        kind_name = "Coscheduling Jobs"
    else:
        MODES = ("job", "mcad", "kueue", "coscheduling")
        logging.error(f"Received an invalid mode: '{mode}'. Must in in {MODES}")
        sys.exit(1)

    logging.info(f"Running with a timespan of {timespan} minutes.")
    timespan_sec = timespan * 60

    job = job_mod.prepare_base_job(namespace, job_template_name, base_name, pod_runtime, pod_requests, pod_count, kueue_mode)
    if job_mode:
        resources = job_mod.prepare_standalone_job(job)
    elif kueue_mode:
        resources = kueue_mod.prepare_kueue_job(job, kueue_queue)
    elif coscheduling_mode:
        resources = coscheduling_mod.prepare_coscheduling_job(job)
    else:
        resources = appwrapper_mod.prepare_appwrapper(namespace, job, priority, pod_count, pod_requests)

    if not resources:
        logging.error("No resource to be created ...")
        sys.exit(1)

    resource_name_template = config.get_config("metadata.name", resources[0])
    resource_json_template = utils.get_json_resource(resources)
    verbose_resource_creation = count < 50

    processes = []
    schedule_result = []
    def _create_resource(index, delay):
        time_fct = (lambda : "{:.2f} minutes".format(float(scheduler.dry_run_time) / 60)) if dry_run \
            else (lambda : datetime.datetime.now().time())

        create_ts = str(time_fct())
        name, process = utils.create_resource(resource_json_template, resource_name_template,
                                                index, verbose_resource_creation, dry_run)
        nonlocal processes
        processes += [process]

        schedule_result.append(dict(
            create=create_ts,
            name=name,
            delay=float(delay),
            index=index
        ))

    times, schedule = scheduler.prepare(_create_resource, distribution, timespan_sec, count,
                                        dry_run=dry_run,
                                        verbose_dry_run=verbose_resource_creation)

    schedule_plan_dest = config.ARTIFACT_DIR / f"schedule_plan.yaml"

    logging.info(f"Saving the schedule plan in {schedule_plan_dest}")
    times_list = times.tolist()
    with open(schedule_plan_dest, "w") as f:
        yaml.dump(dict(zip(range(len(times_list)), times_list)), f)


    print(f"""---\n# Summary: {count} {kind_name}, with each:
#  - {pod_count} Pods with {pod_requests}
#  - running for {pod_runtime} seconds
---
""")

    schedule.run()

    start_wait = datetime.datetime.now()
    if not dry_run:
        for idx, proc in enumerate(processes):
            if (ret := proc.wait()) != 0:
                logging.error(f"Background call #{idx} to '{' '.join(proc.args)}' returned {ret} :/")
                sys.exit(1)

    end_wait = datetime.datetime.now()
    logging.info(f"Had to wait a total of {(end_wait - start_wait).total_seconds():.1f}s to join all the {len(processes)} background processes.")

    schedule_result_dest = config.ARTIFACT_DIR / f"schedule_result.json"

    logging.info(f"Saving the schedule result in {schedule_result_dest}")
    with open(schedule_result_dest, "w") as f:
        json.dump(schedule_result, f)

    if visualize:
        import visualize_schedule
        visualize_schedule.main(config.ARTIFACT_DIR, schedule_result)


if __name__ == "__main__":
    try:
        # Print help rather than opening a pager
        fire.core.Display = lambda lines, out: print(*lines, file=out)

        fire.Fire(main)
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{e.cmd}' failed --> {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print() # empty line after ^C
        logging.error(f"Interrupted.")
        sys.exit(1)
