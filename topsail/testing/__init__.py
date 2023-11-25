import logging
def configure_logging():
    logging.getLogger().setLevel(logging.INFO)

    logging.basicConfig(format='%(asctime)s %(levelname)-4s [%(filename)-10s:%(lineno)3d] %(message)s',
                        datefmt='%H:%M:%S',
                        level=logging.INFO)

def merge_dicts(a, b, path=None):
    "updates a with b"
    if path is None: path = []
    for key in b:
        if key in a and isinstance(a[key], dict) and isinstance(b[key], dict):
            merge_dicts(a[key], b[key], path + [str(key)])
        else:
            a[key] = b[key]
    return a
