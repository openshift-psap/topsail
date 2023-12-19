import os
import pathlib
import time
import traceback
import logging

ARTIFACT_DIR = None

def init():
    global ARTIFACT_DIR

    if "ARTIFACT_DIR" in os.environ:
        ARTIFACT_DIR = pathlib.Path(os.environ["ARTIFACT_DIR"])

    else:
        env_ci_artifact_base_dir = pathlib.Path(os.environ.get("CI_ARTIFACT_BASE_DIR", "/tmp"))
        ARTIFACT_DIR = env_ci_artifact_base_dir / f"ci-artifacts_{time.strftime('%Y%m%d-%H%M')}"
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        os.environ["ARTIFACT_DIR"] = str(ARTIFACT_DIR)


def NextArtifactDir(name):
    next_count = next_artifact_index()
    dirname = ARTIFACT_DIR / f"{next_count:03d}__{name}"
    return TempArtifactDir(dirname)


class TempArtifactDir(object):
    def __init__(self, dirname):
        self.dirname = pathlib.Path(dirname)
        self.previous_dirname = None

    def __enter__(self):
        self.previous_dirname = pathlib.Path(os.environ["ARTIFACT_DIR"])
        os.environ["ARTIFACT_DIR"] = str(self.dirname)
        self.dirname.mkdir(exist_ok=True)

        global ARTIFACT_DIR
        ARTIFACT_DIR = self.dirname

        return True

    def __exit__(self, ex_type, ex_value, exc_traceback):
        global ARTIFACT_DIR

        if ex_value:
            logging.error(f"Caught exception {ex_type.__name__}: {ex_value}")
            with open(ARTIFACT_DIR / "FAILURE", "a") as f:
                print(f"{ex_type.__name__}: {ex_value}", file=f)
                print(''.join(traceback.format_exception(None, value=ex_value, tb=exc_traceback)), file=f)

        os.environ["ARTIFACT_DIR"] = str(self.previous_dirname)
        ARTIFACT_DIR = self.previous_dirname

        return False # If we returned True here, any exception would be suppressed!


def next_artifact_index():
    return len(list(ARTIFACT_DIR.glob("*__*")))
