import matrix_benchmarking.models as matbench_models

#
# lts.KPI_SETTINGS_VERSION must be bumped each time a KPI is added
#

KPIs = {} # populated by the @matbench_models.KPIMetadata decorator

# ---

@matbench_models.KPIMetadata(help="Number of train tokens processed per seconds", unit="tokens/s")
def train_tokens_per_second(lts_payload):
    return lts_payload.results.train_tokens_per_second

@matbench_models.KPIMetadata(help="Number of dataset tokens processed per seconds", unit="tokens/s")
def dataset_tokens_per_second(lts_payload):
    return lts_payload.results.dataset_tokens_per_second

@matbench_models.KPIMetadata(help="Number of dataset tokens processed per seconds per GPU", unit="tokens/s")
def dataset_tokens_per_second_per_gpu(lts_payload):
    return lts_payload.results.dataset_tokens_per_second_per_gpu

@matbench_models.KPIMetadata(help="Number of train tokens processed per GPU per seconds", unit="tokens/s")
def train_tokens_per_gpu_per_second(lts_payload):
    return lts_payload.results.train_tokens_per_gpu_per_second

@matbench_models.KPIMetadata(help="Number of GPU hours required to process a million tokens", unit="hours/Mtoken")
def gpu_hours_per_million_tokens(lts_payload):
    return lts_payload.results.gpu_hours_per_million_tokens

@matbench_models.KPIMetadata(help="Number of samples trained per seconds", unit="samples/s")
def train_samples_per_second(lts_payload):
    return lts_payload.results.train_samples_per_second

@matbench_models.KPIMetadata(help="Time taken to complete the fine-tuning job", unit="s")
def train_runtime(lts_payload):
    return lts_payload.results.train_runtime

@matbench_models.KPIMetadata(help="Number of steps trained per second", unit="steps/s")
def train_steps_per_second(lts_payload):
    return lts_payload.results.train_steps_per_second

@matbench_models.KPIMetadata(help="Average number of tokens", unit="tokens")
def avg_tokens_per_sample(lts_payload):
    return lts_payload.results.avg_tokens_per_sample
