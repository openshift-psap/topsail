import os
import pathlib
import time

ARTIFACT_DIR = None

def init():
    global ARTIFACT_DIR

    if "ARTIFACT_DIR" in os.environ:
        ARTIFACT_DIR = pathlib.Path(os.environ["ARTIFACT_DIR"])

    else:
        env_ci_artifact_base_dir = pathlib.Path(os.environ.get("CI_ARTIFACT_BASE_DIR", "/tmp"))
        ARTIFACT_DIR = env_ci_artifact_base_dir / f"ci-artifacts_{time.strftime('%Y%m%d')}"
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        os.environ["ARTIFACT_DIR"] = str(ARTIFACT_DIR)

class TempArtifactDir(object):
    def __init__(self, dirname):
        self.dirname = dirname
        self.previous_dirname = None

    def __enter__(self):
        self.previous_dirname = pathlib.Path(os.environ["ARTIFACT_DIR"])
        os.environ["ARTIFACT_DIR"] = str(self.dirname)
        self.dirname.mkdir(exist_ok=True)

        global ARTIFACT_DIR
        ARTIFACT_DIR = self.dirname

        return True

    def __exit__(self ,type, value, traceback):
        os.environ["ARTIFACT_DIR"] = str(self.previous_dirname)

        global ARTIFACT_DIR
        ARTIFACT_DIR = self.previous_dirname

        return False

def next_artifact_index():
    return len(list(ARTIFACT_DIR.glob("*__*")))
