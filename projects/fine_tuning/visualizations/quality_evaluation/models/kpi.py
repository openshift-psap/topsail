import matrix_benchmarking.models as matbench_models

#
# lts.KPI_SETTINGS_VERSION must be bumped each time a KPI is added
#

KPIs = {} # populated by the @matbench_models.KPIMetadata decorator

# ---
@matbench_models.KPIMetadata(help="overall accuracy", unit="out of 1")
def overall_accuracy(lts_payload):
    return lts_payload.results.mmlu.["acc,none"]

'''
@matbench_models.KPIMetadata(help="total evaluation time", unit="s")
def total_evaluation_time_seconds(lts_payload):
    return lts_payload.results.total_evaluation_time_seconds
'''

###################for mmlu?
@matbench_models.KPIMetadata(help="accuracies of each mmlu task group", unit="out of 1")
def group_accuracies(lts_payload):
    accuracies = {}
    for group_name, group_data in lts_payload["groups"].items():
        accuracies[group_name] = group_data["acc,none"]
    return accuracies


