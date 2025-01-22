import matrix_benchmarking.models as matbench_models

#
# lts.VERSION must be bumped each time a KPI is added
#

KPIs = {} # populated by the @matbench_models.KPIMetadata decorator

@matbench_models.Format("{:.2f}")
@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Minimum execution time of the benchmark", unit="seconds")
def notebook_performance_benchmark_min_time(lts_payload):
    return min(lts_payload.results.benchmark_measures.measures)


@matbench_models.Format("{:.2f}")
@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Difference between the maximum and minimum execution time of the benchmark", unit="seconds")
def notebook_performance_benchmark_min_max_diff(lts_payload):
    min_value = min(lts_payload.results.benchmark_measures.measures)
    max_value = max(lts_payload.results.benchmark_measures.measures)

    return max_value - min_value

@matbench_models.Format("{:.2f}")
@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="List of the execution time of the benchmark", unit="List[seconds]")
def notebook_performance_benchmark_time(lts_payload):
    return lts_payload.results.benchmark_measures.measures
