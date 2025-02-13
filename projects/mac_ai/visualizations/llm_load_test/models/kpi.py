import matrix_benchmarking.models as matbench_models

#
# lts.KPI_SETTINGS_VERSION must be bumped each time a KPI is added
#

KPIs = {} # populated by the @matbench_models.KPIMetadata decorator

# Throughput

@matbench_models.HigherBetter
@matbench_models.KPIMetadata(help="Model throughput", unit="tokens/s")
def kserve_llm_load_test_throughput(lts_payload):
    return lts_payload.results.throughput


# Time per output token
@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="All values of time per output token", unit="List[ms/token]")
def kserve_llm_load_test_tpot(lts_payload):
    return lts_payload.results.time_per_output_token.values

@matbench_models.LowerBetter
@matbench_models.IgnoredForRegression
@matbench_models.KPIMetadata(help="Min time per output token", unit="ms/token")
def kserve_llm_load_test_tpot_min(lts_payload):
    return lts_payload.results.time_per_output_token.min

@matbench_models.LowerBetter
@matbench_models.IgnoredForRegression
@matbench_models.KPIMetadata(help="Max time per output token", unit="ms/token")
def kserve_llm_load_test_tpot_max(lts_payload):
    return lts_payload.results.time_per_output_token.max

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Median time per output token", unit="ms/token")
def kserve_llm_load_test_tpot_median(lts_payload):
    return lts_payload.results.time_per_output_token.median

@matbench_models.LowerBetter
@matbench_models.IgnoredForRegression
@matbench_models.KPIMetadata(help="Mean time per output token", unit="ms/token")
def kserve_llm_load_test_tpot_mean(lts_payload):
    return lts_payload.results.time_per_output_token.mean

@matbench_models.LowerBetter
@matbench_models.IgnoredForRegression
@matbench_models.KPIMetadata(help="80th Percentile time per output token", unit="ms/token")
def kserve_llm_load_test_tpot_p80(lts_payload):
    return lts_payload.results.time_per_output_token.percentile_80

@matbench_models.LowerBetter
@matbench_models.IgnoredForRegression
@matbench_models.KPIMetadata(help="90th Percentile time per output token", unit="ms/token")
def kserve_llm_load_test_tpot_p90(lts_payload):
    return lts_payload.results.time_per_output_token.percentile_90

@matbench_models.LowerBetter
@matbench_models.IgnoredForRegression
@matbench_models.KPIMetadata(help="95th Percentile time per output token", unit="ms/token")
def kserve_llm_load_test_tpot_p95(lts_payload):
    return lts_payload.results.time_per_output_token.percentile_95

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="99th Percentile time per output token", unit="ms/token")
def kserve_llm_load_test_tpot_p99(lts_payload):
    return lts_payload.results.time_per_output_token.percentile_99

# Inter token latency

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="All values of inter token latency", unit="List[ms]")
def kserve_llm_load_test_itl(lts_payload):
    return lts_payload.results.inter_token_latency.values if lts_payload.results.inter_token_latency else []

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Min inter token latency", unit="ms")
def kserve_llm_load_test_itl_min(lts_payload):
    return lts_payload.results.inter_token_latency.min if lts_payload.results.inter_token_latency else 0

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Max inter token latency", unit="ms")
def kserve_llm_load_test_itl_max(lts_payload):
    return lts_payload.results.inter_token_latency.max if lts_payload.results.inter_token_latency else 0

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Median inter token latency", unit="ms")
def kserve_llm_load_test_itl_median(lts_payload):
    return lts_payload.results.inter_token_latency.median if lts_payload.results.inter_token_latency else 0

@matbench_models.LowerBetter
@matbench_models.IgnoredForRegression
@matbench_models.KPIMetadata(help="Mean inter token latency", unit="ms")
def kserve_llm_load_test_itl_mean(lts_payload):
    return lts_payload.results.inter_token_latency.mean if lts_payload.results.inter_token_latency else 0

@matbench_models.LowerBetter
@matbench_models.IgnoredForRegression
@matbench_models.KPIMetadata(help="80th Percentile inter token latency", unit="ms")
def kserve_llm_load_test_itl_p80(lts_payload):
    return lts_payload.results.inter_token_latency.percentile_80 if lts_payload.results.inter_token_latency else 0

@matbench_models.LowerBetter
@matbench_models.IgnoredForRegression
@matbench_models.KPIMetadata(help="90th Percentile inter token latency", unit="ms")
def kserve_llm_load_test_itl_p90(lts_payload):
    return lts_payload.results.inter_token_latency.percentile_90 if lts_payload.results.inter_token_latency else 0

@matbench_models.LowerBetter
@matbench_models.IgnoredForRegression
@matbench_models.KPIMetadata(help="95th Percentile inter token latency", unit="ms")
def kserve_llm_load_test_itl_p95(lts_payload):
    return lts_payload.results.inter_token_latency.percentile_95 if lts_payload.results.inter_token_latency else 0

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="99th Percentile inter token latency", unit="ms")
def kserve_llm_load_test_itl_p99(lts_payload):
    return lts_payload.results.inter_token_latency.percentile_99 if lts_payload.results.inter_token_latency else 0

# Time to first token

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="All values of time to first token", unit="List[ms]")
def kserve_llm_load_test_ttft(lts_payload):
    return lts_payload.results.time_to_first_token.values if lts_payload.results.time_to_first_token else []

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Min time to first token", unit="ms")
def kserve_llm_load_test_ttft_min(lts_payload):
    return lts_payload.results.time_to_first_token.min if lts_payload.results.time_to_first_token else 0

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Max time to first token", unit="ms")
def kserve_llm_load_test_ttft_max(lts_payload):
    return lts_payload.results.time_to_first_token.max if lts_payload.results.time_to_first_token else 0

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Median time to first token", unit="ms")
def kserve_llm_load_test_ttft_median(lts_payload):
    return lts_payload.results.time_to_first_token.median if lts_payload.results.time_to_first_token else 0

@matbench_models.LowerBetter
@matbench_models.IgnoredForRegression
@matbench_models.KPIMetadata(help="Mean time to first token", unit="ms")
def kserve_llm_load_test_ttft_mean(lts_payload):
    return lts_payload.results.time_to_first_token.mean if lts_payload.results.time_to_first_token else 0

@matbench_models.LowerBetter
@matbench_models.IgnoredForRegression
@matbench_models.KPIMetadata(help="80th Percentile time to first token", unit="ms")
def kserve_llm_load_test_ttft_p80(lts_payload):
    return lts_payload.results.time_to_first_token.percentile_80 if lts_payload.results.time_to_first_token else 0

@matbench_models.LowerBetter
@matbench_models.IgnoredForRegression
@matbench_models.KPIMetadata(help="90th Percentile time to first token", unit="ms")
def kserve_llm_load_test_ttft_p90(lts_payload):
    return lts_payload.results.time_to_first_token.percentile_90 if lts_payload.results.time_to_first_token else 0

@matbench_models.LowerBetter
@matbench_models.IgnoredForRegression
@matbench_models.KPIMetadata(help="95th Percentile time to first token", unit="ms")
def kserve_llm_load_test_ttft_p95(lts_payload):
    return lts_payload.results.time_to_first_token.percentile_95 if lts_payload.results.time_to_first_token else 0

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="99th Percentile time to first token", unit="ms")
def kserve_llm_load_test_ttft_p99(lts_payload):
    return lts_payload.results.time_to_first_token.percentile_99 if lts_payload.results.time_to_first_token else 0

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Number of failure responses", unit="x")
def kserve_llm_load_test_failures(lts_payload):
    return lts_payload.results.failures
