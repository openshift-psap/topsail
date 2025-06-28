import os
import pathlib

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
CONTAINER_BENCH_SECRET_PATH = pathlib.Path(
    os.environ.get("CONTAINER_BENCH_SECRET_PATH", "/env/CONTAINER_BENCH_SECRET_PATH/not_set")
    )
