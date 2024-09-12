import matrix_benchmarking.models as matbench_models
import matrix_benchmarking.parsing.prom as prom_parsing

#
# lts.KPI_SETTINGS_VERSION must be bumped each time a KPI is added
#

KPIs = {} # populated by the @matbench_models.KPIMetadata decorator

# ---

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="placeholder", unit="cores")
def placeholder(lts_payload):
    return 100
