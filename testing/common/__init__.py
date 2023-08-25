import logging
def configure_logging():
    logging.getLogger().setLevel(logging.INFO)

    logging.basicConfig(format='%(asctime)s %(levelname)-4s [%(filename)-10s:%(lineno)3d] %(message)s',
                        datefmt='%H:%M:%S',
                        level=logging.INFO)
