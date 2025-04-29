import matrix_benchmarking.models as matbench_models

#
# lts.KPI_SETTINGS_VERSION must be bumped each time a KPI is added
#

KPIs = {} # populated by the @matbench_models.KPIMetadata decorator

# Throughput

@matbench_models.HigherBetter
@matbench_models.KPIMetadata(help="Model throughput", unit="tokens/s")
def throughput(lts_payload):
    return lts_payload.results.throughput

# Time per output token
@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="All values of time per output token", unit="List[ms/token]")
def tpot(lts_payload):
    return lts_payload.results.time_per_output_token.values if lts_payload.results.time_per_output_token else 0


@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Median time per output token", unit="ms/token")
def tpot_median(lts_payload):
    return lts_payload.results.time_per_output_token.median if lts_payload.results.time_per_output_token else 0

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Mean time per output token", unit="ms/token")
def tpot_mean(lts_payload):
    return lts_payload.results.time_per_output_token.mean if lts_payload.results.time_per_output_token else 0

# Inter token latency

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="All values of inter token latency", unit="List[ms]")
def itl(lts_payload):
    return lts_payload.results.inter_token_latency.values if lts_payload.results.inter_token_latency else []

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Median inter token latency", unit="ms")
def itl_median(lts_payload):
    return lts_payload.results.inter_token_latency.median if lts_payload.results.inter_token_latency else 0

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Mean inter token latency", unit="ms")
def itl_mean(lts_payload):
    return lts_payload.results.inter_token_latency.mean if lts_payload.results.inter_token_latency else 0

# Time to first token

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="All values of time to first token", unit="List[ms]")
def ttft(lts_payload):
    return lts_payload.results.time_to_first_token.values if lts_payload.results.time_to_first_token else []

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Median time to first token", unit="ms")
def ttft_median(lts_payload):
    return lts_payload.results.time_to_first_token.median if lts_payload.results.time_to_first_token else 0

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Mean time to first token", unit="ms")
def ttft_mean(lts_payload):
    return lts_payload.results.time_to_first_token.mean if lts_payload.results.time_to_first_token else 0
