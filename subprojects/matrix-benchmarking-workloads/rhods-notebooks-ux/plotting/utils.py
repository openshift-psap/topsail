from matrix_benchmarking.common import MatrixEntry

import logging

"""
Returns the number of successful users, failed users, and total users
"""
def get_user_info(entry: MatrixEntry) -> (int, int, int):
    success_users = 0
    failed_users = 0

    if entry.is_lts:
        for user in entry.results.users:
            success_users += 1 if user['succeeded'] else 0
            failed_users += 1 if not user['succeeded'] else 0
    else:
        success_users = sum(1 for ods_ci in entry.results.ods_ci.values() if ods_ci.exit_code == 0)
        failed_users = entry.results.user_count - success_users

    return success_users, failed_users, success_users + failed_users


def parse_users(entry: MatrixEntry) -> (int, str, str, int):
    if entry.is_lts:
        for (i, user) in enumerate(entry.results.users):
            for step in user['steps']:
                yield i, step['name'], step['status'], step['duration'], None
    else:
        for user_idx, ods_ci in entry.results.ods_ci.items() if entry.results.ods_ci else []:
            if not ods_ci: continue
            if not getattr(ods_ci, "output", False): continue

            for step_name, step_status in ods_ci.output.items():
                step_duration = (step_status.finish - step_status.start).total_seconds()
                yield user_idx, step_name, step_status.status, step_duration, step_status.start

def get_last_user(entry):
    if entry.is_lts:
        return entry.results.users[-1]
    else:
        return entry.results.ods_ci[max(entry.results.ods_ci.keys())]


def get_last_user_steps(entry: MatrixEntry) -> list:
    last_user = get_last_user(entry)
    if entry.is_lts:
        return last_user['steps']
    else:
        return last_user.output

def get_control_nodes(entry: MatrixEntry) -> list:
    return [node.name for node in entry.results.rhods_cluster_info.control_plane]
