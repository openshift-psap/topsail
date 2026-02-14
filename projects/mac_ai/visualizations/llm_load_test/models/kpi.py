import matrix_benchmarking.models as matbench_models

#
# lts.KPI_SETTINGS_VERSION must be bumped each time a KPI is added
#

KPIs = {} # populated by the @matbench_models.KPIMetadata decorator


@matbench_models.HigherBetter
@matbench_models.KPIMetadata(help="Prompt processing throughput", unit="tokens/s")
def pp_throughput(lts_payload):
    if not lts_payload.results.prompt_processing:
        return None

    return lts_payload.results.prompt_processing.throughput


@matbench_models.HigherBetter
@matbench_models.KPIMetadata(help="Token generation throughput", unit="token/s")
def tg_throughput(lts_payload):
    if not lts_payload.results.token_generation:
        return None

    return lts_payload.results.token_generation.throughput

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Median time to first token", unit="ms")
def llm_load_test_ttft(lts_payload):
    if not lts_payload.results.llm_load_test:
        return None
    if not lts_payload.results.llm_load_test.ttft:
        return None
    return lts_payload.results.llm_load_test.ttft.median


@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Median iter-token latency", unit="ms")
def llm_load_test_itl(lts_payload):
    if not lts_payload.results.llm_load_test:
        return None
    if not lts_payload.results.llm_load_test.itl:
        return None

    return lts_payload.results.llm_load_test.itl.median
