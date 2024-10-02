import os
import pathlib
import time
import traceback
import logging
import threading

###
# The code below required to properly set the ARTIFACT_DIR in the
# thead local storage, so that threads don't share the same
# ARTIFACT_DIR value (and don't update the shared value)
###

class MyThread(threading.Thread):

    def __init__(self, *args, **kwargs):
        super(MyThread, self).__init__(*args, **kwargs)
        self.parent_artifact_dict = None

    def start(self):
        self.parent_artifact_dict = get_tls_artifact_dir()
        super(MyThread, self).start()

    def run(self):
        _set_tls_artifact_dir(self.parent_artifact_dict)
        super(MyThread, self).run()

threading.Thread = MyThread

def __getattr__(name):

    if name == "ARTIFACT_DIR":
        return get_tls_artifact_dir()

    return globals()[name]

_main_artifact_dir = None
_tls_artifact_dir = threading.local()

def get_tls_artifact_dir():
    return _tls_artifact_dir.val


def _set_tls_artifact_dir(value):
    _tls_artifact_dir.val = value

###
# end of the thread local storage code
###

def init():
    if "ARTIFACT_DIR" in os.environ:
        artifact_dir = pathlib.Path(os.environ["ARTIFACT_DIR"])

    else:
        env_topsail_base_dir = pathlib.Path(os.environ.get("TOPSAIL_BASE_DIR", "/tmp"))
        artifact_dir = env_topsail_base_dir / f"topsail_{time.strftime('%Y%m%d-%H%M')}"

        artifact_dir.mkdir(parents=True, exist_ok=True)
        os.environ["ARTIFACT_DIR"] = str(artifact_dir)

    artifact_dir.mkdir(parents=True, exist_ok=True)
    _set_tls_artifact_dir(artifact_dir)


def NextArtifactDir(name, *, lock=None, counter_p=None):
    if lock:
        with lock:
            next_count = counter_p[0]
            counter_p[0] += 1
    else:
        next_count = next_artifact_index()

    dirname = get_tls_artifact_dir() / f"{next_count:03d}__{name}"

    return TempArtifactDir(dirname)


class TempArtifactDir(object):
    def __init__(self, dirname):
        self.dirname = pathlib.Path(dirname)
        self.previous_dirname = None

    def __enter__(self):
        self.previous_dirname = get_tls_artifact_dir()
        os.environ["ARTIFACT_DIR"] = str(self.dirname)
        self.dirname.mkdir(exist_ok=True)

        _set_tls_artifact_dir(self.dirname)

        return True

    def __exit__(self, ex_type, ex_value, exc_traceback):
        global _ARTIFACT_DIR

        if ex_value:
            logging.error(f"Caught exception {ex_type.__name__}: {ex_value}")
            with open(get_tls_artifact_dir() / "FAILURE", "a") as f:
                print(f"{ex_type.__name__}: {ex_value}", file=f)
                print(''.join(traceback.format_exception(None, value=ex_value, tb=exc_traceback)), file=f)

        os.environ["ARTIFACT_DIR"] = str(self.previous_dirname)
        _set_tls_artifact_dir(self.previous_dirname)

        return False # If we returned True here, any exception would be suppressed!


def next_artifact_index():
    return len(list(get_tls_artifact_dir().glob("*__*")))
