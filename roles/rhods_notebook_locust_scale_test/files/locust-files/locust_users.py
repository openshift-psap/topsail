# based on https://github.com/locustio/locust/blob/master/examples/custom_messages.py

import logging
import math

from locust import HttpUser, task, events, between
from locust.runners import MasterRunner, WorkerRunner

env = None # set by locustfile.py
ready = False
user_indexes = []

def setup_test_users(environment, msg, **kwargs):
    # Fired when the worker receives a message of type 'test_users'
    user_indexes.extend(map(lambda u: int(u["uid"]), msg.data))
    environment.runner.send_message("acknowledge_users", f"Thanks for the {len(msg.data)} users! {user_indexes}")
    global ready
    ready = True
    env.start_event.fire(dict(request_type="USER_RECEIVED"))

    if not user_indexes:
        logging.info(f"Worker {environment.runner} has no work, quitting.")
        environment.runner.quit()
    else:
        logging.info(f"Worker received users {user_indexes}")


def on_acknowledge(msg, **kwargs):
    # Fired when the master receives a message of type 'acknowledge_users'
    logging.warning(msg.data)


@events.init.add_listener
def on_locust_init(environment, **_kwargs):
    if environment.runner is None:
        user_indexes.append(0)
        global ready
        ready = True
        env.start_event.fire(dict(request_type="USER_RECEIVED"))

        return

    if not isinstance(environment.runner, MasterRunner):
        environment.runner.register_message("test_users", setup_test_users)
    if not isinstance(environment.runner, WorkerRunner):
        environment.runner.register_message("acknowledge_users", on_acknowledge)


@events.test_start.add_listener
def on_test_start(environment, **_kwargs):
    if environment.runner is None:
        return

    # When the test is started, evenly divides list between
    # worker nodes to ensure unique data across threads
    if not isinstance(environment.runner, WorkerRunner):
        users = []
        for uid in range(environment.runner.target_user_count):
            users.append({"uid": uid})

        worker_count = environment.runner.worker_count
        print("len_count", len(users))
        print("worker_count", worker_count)
        chunk_size = math.ceil(len(users) / worker_count)

        for i, worker in enumerate(environment.runner.clients):
            start_index = i * chunk_size

            if i + 1 < worker_count:
                end_index = start_index + chunk_size
            else:
                end_index = len(users)

            data = users[start_index:end_index]
            logging.info(f"Sending users {[d['uid'] for d in data]} to worker #{i} {worker}")

            environment.runner.send_message("test_users", data, worker)
