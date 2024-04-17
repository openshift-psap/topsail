import matrix_benchmarking.models as matbench_models

#
# lts.KPI_SETTINGS_VERSION must be bumped each time a KPI is added
#

KPIs = {} # populated by the @matbench_models.KPIMetadata decorator

@matbench_models.KPIMetadata(help="Time to complete the test", unit="s")
def time_to_test_sec(lts_payload):
    return lts_payload.results.time_to_test_sec

@matbench_models.KPIMetadata(help="Time to the scheduling of the last workload", unit="s")
def time_to_last_launch_sec(lts_payload):
    return lts_payload.results.time_to_last_schedule_sec
