# --- Prepare module --- #

def prepare_test(base_work_dir, platform):
    pass

def get_binary_path(base_work_dir, platform):
    pass

def prepare_binary(base_work_dir, platform):
    pass

# --- Test module --- #

def unload_model(base_work_dir, inference_server_path, model_name, platform):
    pass

def pull_model(base_work_dir, inference_server_native_path, model_name, model_fname):
    pass

def run_benchmark(base_work_dir, inference_server_path, model_fname):
    pass

def run_model(base_work_dir, inference_server_path, model_fname):
    pass
