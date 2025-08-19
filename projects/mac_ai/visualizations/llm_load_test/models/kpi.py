import matrix_benchmarking.models as matbench_models

#
# lts.KPI_SETTINGS_VERSION must be bumped each time a KPI is added
#

KPIs = {} # populated by the @matbench_models.KPIMetadata decorator


@matbench_models.HigherBetter
@matbench_models.KPIMetadata(help="Prompt processing throughput", unit="tokens/s")
def pp_throughput(lts_payload):
    return lts_payload.results.prompt_processing.throughput


@matbench_models.HigherBetter
@matbench_models.KPIMetadata(help="Token generation throughput", unit="token/ms")
def tg_throughput(lts_payload):
    return lts_payload.results.token_generation.throughput
