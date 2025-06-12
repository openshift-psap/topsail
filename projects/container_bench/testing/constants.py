import os
import pathlib

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
CRC_CONTAINER_BENCH_SECRET_PATH = pathlib.Path(
    os.environ.get("CRC_MAC_AI_SECRET_PATH", "/env/CRC_CONTAINER_BENCH_SECRET_PATH/not_set")
    )
