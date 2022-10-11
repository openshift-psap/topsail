import gevent
import os
import pickle
import json
import types

import locust
import locust_plugins
from locust import HttpUser, task
from bs4 import BeautifulSoup

from locust_plugins.users import HttpUserWithResources
from locust.exception import StopUser

import urllib3
import urllib3.util.url
urllib3.disable_warnings()

import oauth
import dashboard
import notebook
import jupyterlab

env = types.SimpleNamespace()
env.DASHBOARD_HOST = os.getenv("ODH_DASHBOARD_URL")
env.USERNAME_PREFIX = os.getenv("TEST_USERS_USERNAME_PREFIX")
env.JOB_COMPLETION_INDEX = os.getenv("JOB_COMPLETION_INDEX", 0)
env.IDP_NAME = os.getenv("TEST_USERS_IDP_NAME")
env.NAMESPACE = "rhods-notebooks"

env.NOTEBOOK_IMAGE_NAME = os.getenv("NOTEBOOK_IMAGE_NAME")
env.NOTEBOOK_SIZE_NAME = os.getenv("NOTEBOOK_SIZE_NAME")
env.USER_INDEX_OFFSET = int(os.getenv("USER_INDEX_OFFSET", 0))
env.SAVE_COOKIES = True
env.DO_NOT_STOP_NOTEBOOK = False

# Other env variables:
# - LOCUST_USERS (number of users)
# - LOCUST_RUN_TIME (locust test duration)
# - LOCUST_SPAWN_RATE (locust number of new users per seconds)
# - LOCUST_LOCUSTFILE (locustfile.py file that will be executed)

creds_file = os.getenv("CREDS_FILE")
env.USER_PASSWORD = None
with open(creds_file) as f:
    for line in f:
        if not line.startswith("user_password="): continue
        env.USER_PASSWORD = line.strip().split("=")[1]

class NotebookUser(HttpUser):
    host = env.DASHBOARD_HOST
    verify = False
    user_next_id = env.USER_INDEX_OFFSET
    default_resource_filter = f'/A(?!{env.DASHBOARD_HOST}/data:image:)'
    bundle_resource_stats = False

    def __init__(self, locust_env):
        HttpUser.__init__(self, locust_env)

        self.locust_env = locust_env
        self.client.verify = False

        self.loop = 0
        self.user_id = self.__class__.user_next_id
        self.user_name = f"{env.USERNAME_PREFIX}{self.user_id}"
        self.__class__.user_next_id += 1

        self.oauth = oauth.Oauth(self.client, env, self.user_name)
        self.dashboard = dashboard.Dashboard(self.client, env, self.user_name, self.oauth)
        self.notebook = notebook.Notebook(self.client, env, self.user_name)
        self.jupyterlab = jupyterlab.JupyterLab(self.client, env, self.user_name, self.oauth)

    def on_start(self):
        print(f"Running user #{self.user_name}")

        if env.SAVE_COOKIES:
            try:
                with open(f"cookies.{self.user_id}.pickle", "rb") as f:
                    self.client.cookies.update(pickle.load(f))
            except FileNotFoundError: pass # ignore
            except EOFError: pass # ignore

        if not self.dashboard.go_to_dashboard():
            print("Failed to go to RHODS dashboard")
            return False

        if env.SAVE_COOKIES:
            with open(f"cookies.{self.user_id}.pickle", "wb") as f:
                pickle.dump(self.client.cookies, f)

    @task
    def launch_a_notebook(self):
        print("launch_a_notebook")
        if __name__ == "__main__" and self.loop != 0:
            raise StopUser()
        first = self.loop == 0
        self.loop += 1

        self.notebook.stop()

        notebook_json = self.notebook.launch(first)

        self.jupyterlab.get_jupyterlab_page()

        self.notebook.stop()

        if __name__ == "__main__":
            raise StopUser()

    def on_stop(self):
        self.notebook.stop()


if __name__ == "__main__":
    locust.run_single_user(NotebookUser)
