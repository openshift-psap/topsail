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

@matbench_models.KPIMetadata(help="Max total GPU memory usage, for the sum of all the GPUs | DCGM_FI_DEV_FB_USED", unit="bytes")
def gpu_total_memory_usage_max(lts_payload):
    metrics = lts_payload.results.metrics.gpu_total_memory_used

    if not metrics:
        return -1

    return prom_parsing.single_max(metrics)[0]

# ---

@matbench_models.KPIMetadata(help="Mean (of the mean) GPU compute usage", unit="%")
def gpu_compute_usage_mean(lts_payload):
    metrics = lts_payload.results.metrics.gpu_active_computes

    if not metrics:
        return -1

    return prom_parsing.mean_mean(metrics)

@matbench_models.KPIMetadata(help="Max (of the mean) GPU compute usage", unit="%")
def gpu_compute_usage_max(lts_payload):
    metrics = lts_payload.results.metrics.gpu_active_computes

    if not metrics:
        return -1

    return prom_parsing.max_mean(metrics)

@matbench_models.KPIMetadata(help="Min (of the mean) GPU compute usage", unit="%")
def gpu_compute_usage_min(lts_payload):
    metrics = lts_payload.results.metrics.gpu_active_computes

    if not metrics:
        return -1

    return prom_parsing.min_mean(metrics)

# ---

@matbench_models.KPIMetadata(help="Mean (of the mean) GPU memory usage", unit="bytes")
def gpu_memory_usage_mean(lts_payload):
    metrics = lts_payload.results.metrics.gpu_memory_used

    if not metrics:
        return -1

    return prom_parsing.mean_mean(metrics)

@matbench_models.KPIMetadata(help="Max (of the mean) GPU memory usage", unit="bytes")
def gpu_memory_usage_max(lts_payload):
    metrics = lts_payload.results.metrics.gpu_memory_used

    if not metrics:
        return -1

    return prom_parsing.max_mean(metrics)

@matbench_models.KPIMetadata(help="Min (of the mean) GPU memory usage", unit="bytes")
def gpu_memory_usage_min(lts_payload):
    metrics = lts_payload.results.metrics.gpu_memory_used

    if not metrics:
        return -1

    return prom_parsing.min_mean(metrics)

@matbench_models.KPIMetadata(help="Peak GPU memory usage", unit="bytes")
def gpu_memory_usage_peak(lts_payload):
    metrics = lts_payload.results.metrics.gpu_memory_used

    if not metrics:
        return -1

    return prom_parsing.max_max(metrics)

# ---

@matbench_models.KPIMetadata(help="Mean CPU usage", unit="cores")
def cpu_usage_mean(lts_payload):
    metrics = lts_payload.results.metrics.cpu_usage

    if not metrics:
        return -1

    return prom_parsing.single_mean(metrics)[0]

@matbench_models.KPIMetadata(help="Mean memory usage", unit="bytes")
def memory_usage_mean(lts_payload):
    metrics = lts_payload.results.metrics.memory_usage

    if not metrics:
        return -1

    return prom_parsing.single_mean(metrics)[0]
