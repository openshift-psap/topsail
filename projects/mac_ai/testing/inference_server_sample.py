# --- Prepare module --- #

def prepare_test(base_work_dir, platform):
    # update the config file here for the test step, if needed
    pass

def get_binary_path(base_work_dir, platform):
    # return the path to the inference server binary, for the given platform
    pass

def prepare_binary(base_work_dir, platform):
    # build the inference server binary, for the given platform
    pass


# --- Test module --- #

def start_server(base_work_dir, inference_server_native_path):
    # start the inference server (or do nothing)
    pass

def stop_server(base_work_dir, inference_server_native_path):
    # stop the inference server (or do nothing)
    pass

def has_model(base_work_dir, inference_server_native_path, model_name):
    # tell if the model is available locally
    # assumes start_server was called before
    pass

def pull_model(base_work_dir, inference_server_native_path, model_name):
    # download the model locally
    # assumes start_server was called before
    pass

def run_benchmark(base_work_dir, inference_server_path, model_fname):
    # optional
    # runs an inference server internal benchmark
    pass

def run_model(base_work_dir, inference_server_path, model_fname):
    # *returns the model_id to pass to llm-load-test*
    # assumes start_server was called before
    pass

def unload_model(base_work_dir, inference_server_path, model_name, platform):
    # assumes start_server was called before
    pass

def delete_models(base_work_dir, inference_server_path):
    # optional if the models are stored with `model_to_fname(model)`
    # assumes start_server was called before
    pass
