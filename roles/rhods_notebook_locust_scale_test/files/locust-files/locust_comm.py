from locust import events
from locust.runners import MasterRunner, WorkerRunner

counter = 0
def on_request_user(environment, msg, **kwargs):
    global counter
    counter += 1
    print("SEND USER", counter)
    environment.runner.send_message('receive_user', counter)

def on_receive_user(environment, msg, **kwargs):
    print("Received", msg.data)

@events.init.add_listener
def on_locust_init(environment, **_kwargs):
    if not isinstance(environment.runner, WorkerRunner): # is master
        environment.runner.register_message('request_user', on_request_user)

    if not isinstance(environment.runner, MasterRunner): # is worker
        environment.runner.register_message('receive_user', on_receive_user)



@events.test_start.add_listener
def on_test_start(environment, **_kwargs):
    if not isinstance(environment.runner, WorkerRunner):  # is master

        environment.runner.send_message('test_users', counter)

    if not isinstance(environment.runner, MasterRunner): # is worker
        environment.runner.send_message('request_user')
