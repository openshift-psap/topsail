import types
import logging

def _get_time_to_cleanup(results):
    start = results.cleanup_times.start
    end = results.cleanup_times.end
    if not (start and end):
        return 0

    return (end - start).total_seconds()


def _get_time_to_last_launch(results):
    if not results.resource_times:
        return 0, None


    target_kind = {"job": "Job",
            "mcad": "AppWrapper",
            "kueue": "Job"}[results.test_case_properties.mode]

    resource_time = sorted([resource_time for resource_time in results.resource_times.values() if resource_time.kind == target_kind], key=lambda t: t.creation)[-1]

    start_time = results.test_start_end_time.start

    last_launch = resource_time.creation
    return (last_launch - start_time).total_seconds(), last_launch


def _get_time_to_last_schedule(results):
    if not results.pod_times:
        return 0, None

    pod_time = sorted(results.pod_times, key=lambda t: t.pod_scheduled)[-1]

    start_time = results.test_start_end_time.start

    last_schedule = pod_time.pod_scheduled
    return (last_schedule - start_time).total_seconds(), last_schedule


def generate_lts_results(results):
    results_lts = types.SimpleNamespace()

    results_lts.time_to_last_schedule_sec, last_schedule_time = \
        _get_time_to_last_schedule(results)

    results_lts.time_to_last_launch_sec, last_launch_time = \
        _get_time_to_last_launch(results)

    results_lts.last_launch_to_last_schedule_sec = \
        (last_schedule_time - last_launch_time).total_seconds() \
        if last_schedule_time and last_launch_time else None

    results_lts.time_to_cleanup_sec = \
        _get_time_to_cleanup(results)

    return results_lts
