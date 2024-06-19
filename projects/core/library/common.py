from . import run

def prepare_light_cluster():
    run.run_toolbox("cluster", "wait_fully_awake")


def cleanup_cluster():
    pass
