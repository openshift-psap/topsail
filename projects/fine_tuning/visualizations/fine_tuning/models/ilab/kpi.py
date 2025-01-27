import matrix_benchmarking.models as matbench_models

#
# lts.KPI_SETTINGS_VERSION must be bumped each time a KPI is added
#

KPIs = {} # populated by the @matbench_models.KPIMetadata decorator

# ---

@matbench_models.Format("{:.2f}")
@matbench_models.HigherBetter
@matbench_models.KPIMetadata(help="Fine-tuning average throughput", unit="samples/s")
def average_throughput(lts_payload):
    return lts_payload.results.average_throughput
