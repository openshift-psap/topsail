import matrix_benchmarking.models as matbench_models
import matrix_benchmarking.parsing.prom as prom_parsing

#
# lts.KPI_SETTINGS_VERSION must be bumped each time a KPI is added
#

KPIs = {} # populated by the @matbench_models.KPIMetadata decorator

# ---

@matbench_models.FormatDivisor(1024*1024*1024, unit="GB", format="{:.2f}")
@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Total network transmit usage per NIC and Pod", unit="list[bytes]")
def network_total_usage_per_nic(lts_payload):
    metrics = lts_payload.results.metrics.network_total_usage

    if not metrics:
        return [-1]

    return last_substract_first_values(metrics)


@matbench_models.FormatDivisor(1024*1024*1024, unit="GB", format="{:.2f}")
@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Total network transmit usage, for all NICs", unit="bytes")
def network_total_usage(lts_payload):
    metrics = lts_payload.results.metrics.network_total_usage

    if not metrics:
        return -1

    return sum(last_substract_first_values(metrics))


@matbench_models.FormatDivisor(1024, unit="GB", format="{:.2f}")
@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Total GPU memory usage", unit="MB")
def gpu_memory_total_usage(lts_payload):
    metrics = lts_payload.results.metrics.gpu_memory_total_usage

    if not metrics:
        return -1

    return prom_parsing.single_max(metrics)[0]



def last_substract_first_values(_metrics):
    def substract_first(metrics):
        all_values = []
        for metric in metrics:
            first = next(metric.values.items().__iter__())[1]
            values = [v - first for v in metric.values.values()]
            all_values.append(values)
        return all_values

    def last(all_values):
        lasts = []
        for values in all_values:
            lasts.append(values[-1])

        return lasts

    return last(substract_first(_metrics))
