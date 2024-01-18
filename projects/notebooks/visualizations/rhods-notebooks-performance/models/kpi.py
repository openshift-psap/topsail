import matrix_benchmarking.models as matbench_models

KPIs = {} # populated by the @matbench_models.KPIMetadata decorator

class NotebookPerformanceKPI(matbench_models.KPI):
    rhoai_version: matbench_models.SemVer
    ocp_version: matbench_models.SemVer
    image: str
    image_tag: str
    image_name: str
    instance_type: str
    benchmark_name: str


@matbench_models.KPIMetadata(help="minimum execution time of the benchmark", unit="seconds")
def notebook_performance_benchmark_min_time(lts_payload):
    return min(lts_payload.results.benchmark_measures.measures)


@matbench_models.KPIMetadata(help="difference between the maximum and minimum execution time of the benchmark", unit="seconds")
def notebook_performance_benchmark_min_max_diff(lts_payload):
    min_value = min(lts_payload.results.benchmark_measures.measures)
    max_value = max(lts_payload.results.benchmark_measures.measures)

    return max_value - min_value
