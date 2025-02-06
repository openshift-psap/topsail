from matrix_benchmarking.common import MatrixEntry

import logging

"""
Returns the number of successful users, failed users, and total users
"""
def get_user_info(entry: MatrixEntry) -> (int, int, int):
    success_users = 0
    failed_users = 0

    success_users = sum(1 for ods_ci in entry.results.ods_ci.values() if ods_ci.exit_code == 0)
    failed_users = entry.results.user_count - success_users

    return success_users, failed_users, success_users + failed_users


def parse_users(entry: MatrixEntry) -> (int, str, str, int):
    for user_idx, ods_ci in entry.results.ods_ci.items() if entry.results.ods_ci else []:
        if not ods_ci: continue
        if not getattr(ods_ci, "output", False): continue

        for step_name, step_status in ods_ci.output.items():
            step_duration = (step_status.finish - step_status.start).total_seconds()
            yield user_idx, step_name, step_status.status, step_duration, step_status.start

def get_last_user(entry):
    return entry.results.ods_ci[max(entry.results.ods_ci.keys())]


def get_last_user_steps(entry: MatrixEntry) -> list:
    last_user = get_last_user(entry)
    return last_user.output

def get_control_nodes(entry: MatrixEntry) -> list:
    return [node.name for node in entry.results.cluster_info.control_plane]
