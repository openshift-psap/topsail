import matrix_benchmarking.models as matbench_models

#
# lts.KPI_SETTINGS_VERSION must be bumped each time a KPI is added
#

KPIs = {} # populated by the @matbench_models.KPIMetadata decorator


@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="All values of the run latency", unit="List[sec]")
def dsp_run_latency(lts_payload):
    return lts_payload.results.run_latency.values

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Min run latency", unit="sec")
def dsp_run_latency_min(lts_payload):
    return lts_payload.results.run_latency.min

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Max run latency", unit="sec")
def dsp_run_latency_max(lts_payload):
    return lts_payload.results.run_latency.max

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Median run latency", unit="sec")
def dsp_run_latency_median(lts_payload):
    return lts_payload.results.run_latency.median

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="All values of the run duration", unit="List[sec]")
def dsp_run_duration(lts_payload):
    return lts_payload.results.run_duration.values

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Min run duration", unit="sec")
def dsp_run_duration_min(lts_payload):
    return lts_payload.results.run_duration.min

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Max run duration", unit="sec")
def dsp_run_duration_max(lts_payload):
    return lts_payload.results.run_duration.max

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Median run duration", unit="sec")
def dsp_run_duration_median(lts_payload):
    return lts_payload.results.run_duration.median

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Seconds that run latency increases per run", unit="sec/run")
def dsp_run_latency_degrade_speed(lts_payload):
    return lts_payload.results.run_latency.degrade_speed

@matbench_models.LowerBetter
@matbench_models.KPIMetadata(help="Seconds that run duration increases per run", unit="sec/run")
def dsp_run_duration_degrade_speed(lts_payload):
    return lts_payload.results.run_duration.degrade_speed
