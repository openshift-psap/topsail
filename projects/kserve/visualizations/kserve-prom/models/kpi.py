import matrix_benchmarking.models as matbench_models
import matrix_benchmarking.parsing.prom as prom_parsing

#
# lts.KPI_SETTINGS_VERSION must be bumped each time a KPI is added
#

KPIs = {} # populated by the @matbench_models.KPIMetadata decorator

# ---

@matbench_models.KPIMetadata(help="Max CPU usage of the Kserve container | container_cpu_usage_seconds_total", unit="cores")
def kserve_container_cpu_usage_max(lts_payload):
    return prom_parsing.all_max(lts_payload.results.metrics.kserve_container_cpu_usage)[0]

@matbench_models.KPIMetadata(help="Max memory usage of the Kserve container | container_memory_usage_bytes", unit="bytes")
def kserve_container_memory_usage_max(lts_payload):
    return prom_parsing.all_max(lts_payload.results.metrics.kserve_container_memory_usage)[0]

# ---

@matbench_models.KPIMetadata(help="CPU footprint (request) of the RHOAI namespaces | kube_pod_container_resource_requests{resource='cpu'}", unit="cores")
def footprint_rhoai_namespace_cpu_request(lts_payload):
    return prom_parsing.single_max(lts_payload.results.metrics.rhoai_cpu_footprint_model_request)[0]

@matbench_models.KPIMetadata(help="Memory footprint (request) of the RHOAI namespaces | kube_pod_container_resource_requests{resource='memory'}", unit="bytes")
def footprint_rhoai_namespace_memory_request(lts_payload):
    return prom_parsing.single_max(lts_payload.results.metrics.rhoai_mem_footprint_model_request)[0]

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
