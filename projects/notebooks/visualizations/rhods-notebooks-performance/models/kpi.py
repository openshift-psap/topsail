import matrix_benchmarking.models as matbench_models

#
# lts.VERSION must be bumped each time a KPI is added
#

KPIs = {} # populated by the @matbench_models.KPIMetadata decorator


@matbench_models.KPIMetadata(help="minimum execution time of the benchmark", unit="seconds", lower_better=True)
def notebook_performance_benchmark_min_time(lts_payload):
    return min(lts_payload.results.benchmark_measures.measures)


@matbench_models.KPIMetadata(help="difference between the maximum and minimum execution time of the benchmark", unit="seconds", lower_better=True)
def notebook_performance_benchmark_min_max_diff(lts_payload):
    min_value = min(lts_payload.results.benchmark_measures.measures)
    max_value = max(lts_payload.results.benchmark_measures.measures)

    return max_value - min_value


@matbench_models.KPIMetadata(help="list of the execution time of the benchmark", unit="seconds", lower_better=True)
def notebook_performance_benchmark_time(lts_payload):
    return lts_payload.results.benchmark_measures.measures
