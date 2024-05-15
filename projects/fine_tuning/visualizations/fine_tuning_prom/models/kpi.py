import matrix_benchmarking.models as matbench_models
import matrix_benchmarking.parsing.prom as prom_parsing

#
# lts.KPI_SETTINGS_VERSION must be bumped each time a KPI is added
#

KPIs = {} # populated by the @matbench_models.KPIMetadata decorator

# ---

@matbench_models.KPIMetadata(help="Max GPU memory usage, per GPU | DCGM_FI_DEV_FB_USED", unit="list(bytes)")
def gpu_memory_usage_max_per_gpu(lts_payload):
    metrics = lts_payload.results.metrics.gpu_memory_used

    if not metrics:
        return [-1]

    return prom_parsing.all_max(metrics)

@matbench_models.KPIMetadata(help="Max GPU memory usage, for any of the GPUs | DCGM_FI_DEV_FB_USED", unit="bytes")
def gpu_memory_usage_max_all_gpus(lts_payload):
    metrics = lts_payload.results.metrics.gpu_memory_used

    if not metrics:
        return -1

    return prom_parsing.max_max(metrics)

@matbench_models.KPIMetadata(help="Max total GPU memory usage, for all the GPUs | DCGM_FI_DEV_FB_USED", unit="bytes")
def gpu_total_memory_usage_max(lts_payload):
    metrics = lts_payload.results.metrics.gpu_total_memory_used

    if not metrics:
        return -1

    return prom_parsing.single_max(metrics)[0]
