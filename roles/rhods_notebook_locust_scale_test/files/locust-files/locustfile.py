import gevent
import os
import pickle
import json
import types
import logging
logging.getLogger().setLevel(logging.INFO)
import time

import locust
import locust_plugins
from locust import HttpUser, task
from bs4 import BeautifulSoup

from locust_plugins.users import HttpUserWithResources
from locust.exception import StopUser

import urllib3
import urllib3.util.url
urllib3.disable_warnings()

import common
import oauth
import dashboard
import workbench
import jupyterlab

import locust_users

locust_users.env = common.env = env = types.SimpleNamespace()

env.DASHBOARD_HOST = os.getenv("ODH_DASHBOARD_URL")
env.USERNAME_PREFIX = os.getenv("TEST_USERS_USERNAME_PREFIX")
env.JOB_COMPLETION_INDEX = os.getenv("JOB_COMPLETION_INDEX", 0)
env.IDP_NAME = os.getenv("TEST_USERS_IDP_NAME")
env.NAMESPACE = "rhods-notebooks"
env.JOB_COMPLETION_INDEX = int(os.getenv("JOB_COMPLETION_INDEX", 0))
env.RESULTS_DEST = os.getenv("RESULTS_DEST")

env.NOTEBOOK_IMAGE_NAME = os.getenv("NOTEBOOK_IMAGE_NAME")
env.NOTEBOOK_SIZE_NAME = os.getenv("NOTEBOOK_SIZE_NAME")
env.USER_INDEX_OFFSET = int(os.getenv("USER_INDEX_OFFSET", 0))
env.USER_SLEEP_FACTOR = float(os.getenv("USER_SLEEP_FACTOR"))
env.REUSE_COOKIES = os.getenv("REUSE_COOKIES", False) == "1"
env.WORKER_COUNT = int(os.getenv("WORKER_COUNT", 1))
env.DEBUG_MODE = os.getenv("DEBUG_MODE", False) == "1"
env.DO_NOT_STOP_NOTEBOOK = False
env.SKIP_OPTIONAL = os.getenv("SKIP_OPTIONAL", "1") == "1"

env.LOCUST_USERS = int(os.getenv("LOCUST_USERS"))

# Other env variables:
# - LOCUST_USERS (number of users)
# - LOCUST_RUN_TIME (locust test duration)
# - LOCUST_SPAWN_RATE (locust number of new users per seconds)
# - LOCUST_LOCUSTFILE (locustfile.py file that will be executed)

env.LOCUST_CSV = os.getenv("LOCUST_CSV")

creds_file = os.getenv("CREDS_FILE")
env.USER_PASSWORD = None
with open(creds_file) as f:
    for line in f:
        if not line.startswith("user_password="): continue
        env.USER_PASSWORD = line.strip().split("=")[1]

env.csv_progress = common.CsvFileWriter(f"{env.RESULTS_DEST}_worker{env.JOB_COMPLETION_INDEX}_progress.csv", common.CsvProgressEntry)
env.csv_bug_hits = common.CsvFileWriter(f"{env.RESULTS_DEST}_worker{env.JOB_COMPLETION_INDEX}_bug_hits.csv", common.CsvBugHitEntry)

env.start_event.__enter__()
env.start_event.fire(dict(request_type="PROCESS_STARTED"))

class WorkbenchUser(HttpUser):
    host = env.DASHBOARD_HOST
    verify = False

    default_resource_filter = f'/A(?!{env.DASHBOARD_HOST}/data:image:)'
    bundle_resource_stats = False

    @locust.events.test_start.add_listener
    def on_test_start(environment, **_kwargs):
        if not env.JOB_COMPLETION_INDEX:
            from locust.runners import MasterRunner, WorkerRunner
            if isinstance(environment.runner, WorkerRunner):
                env.JOB_COMPLETION_INDEX = environment.runner.worker_index
                logging.info(f"JOB_COMPLETION_INDEX=0 overriden to {environment.runner.worker_index=}")

        logging.info(f"Worker {env.JOB_COMPLETION_INDEX} is in charge of users {locust_users.user_indexes}")

    def __init__(self, locust_env):
        HttpUser.__init__(self, locust_env)

        self.locust_env = locust_env
        self.client.verify = False

        self.loop = 0

        while not locust_users.ready:
            print("not ready")
            time.sleep(1)

        if not locust_users.user_indexes:
            self.environment.runner.quit()

        self.user_index = locust_users.user_indexes.pop()
        self.user_name = f"{env.USERNAME_PREFIX}{env.USER_INDEX_OFFSET + self.user_index}"
        logging.warning(f"Starting user '{self.user_name}'.")


        self.project_name = self.user_name
        self.workbench_name = self.user_name
        self.workbench_route = None

        self.__context = common.Context(self.client, env, self.user_name, self.user_index) # self.context is used by Locust :/
        self.oauth = oauth.Oauth(self.__context)
        self.dashboard = dashboard.Dashboard(self.__context, self.oauth)
        self.workbench = workbench.Workbench(self.__context)
        self.jupyterlab = jupyterlab.JupyterLab(self.__context, self.oauth)

        self.workbench_obj = None

    def on_start(self):
        logging.info(f"Running user #{self.user_name}")

        if env.REUSE_COOKIES:
            self.cookies_filename = f".cookies.{self.user_name}.pickle"

            try:
                with open(self.cookies_filename, "rb") as f:
                    self.client.cookies.update(pickle.load(f))
            except FileNotFoundError: pass # ignore
            except EOFError: pass # ignore

    def initialize(self):
        @common.Step("launch_delay")
        def sleep_delay(_dashboard_self):
            sleep_delay = self.user_index * env.USER_SLEEP_FACTOR
            logging.info(f"{self.user_name}: sleep for {sleep_delay:.1f}s before running.")
            time.sleep(sleep_delay)
            logging.info(f"{self.user_name}: done sleeping.")

        sleep_delay(self.dashboard)

        if not self.dashboard.connect_to_the_dashboard():
            logging.error("Failed to go to RHODS dashboard")
            return False

        if env.REUSE_COOKIES:
            with open(self.cookies_filename, "wb") as f:
                pickle.dump(self.client.cookies, f)

    @task
    def launch_a_workbench(self):
        if __name__ == "__main__" and self.loop != 0:
            # execution crashed before reaching the end of this function
            raise SystemExit(1)

        if self.loop != 0:
            # we currently want to run only once
            logging.info(f"END: launch_a_workbench #{self.loop}, "
                         f"user={self.user_name}, worker={env.JOB_COMPLETION_INDEX}")

            self.environment.runner.quit()

        first = self.loop == 0
        logging.info(f"TASK: launch_a_workbench #{self.loop}, "
                     f"user={self.user_name}, worker={env.JOB_COMPLETION_INDEX}")
        self.loop += 1

        if first:
            self.initialize()
            self.dashboard.fetch_the_dashboard_frontend()

        self.dashboard.load_the_dashboard()

        k8s_project, k8s_workbenches = self.dashboard.go_to_the_project_page(self.project_name)

        try:
            self.workbench_obj, self.workbench_route = self.dashboard.create_and_start_the_workbench(k8s_project, k8s_workbenches, self.workbench_name)

            self.jupyterlab.go_to_jupyterlab_page(self.workbench_obj, self.workbench_route)

        except common.ScaleTestError as e:
            # catch the Exception, so that Locust doesn't track it.
            # it has already been recorded as part of common.LocustMetaEvent context manager.
            logging.error(f"{e.__class__.__name__}: {e}")

        finally:
            if self.workbench_obj:
                self.workbench_obj.stop()
            self.k8s_workbench = None

        if __name__ == "__main__":
            raise StopUser()

    def on_stop(self):
        if not self.workbench_obj: return

        self.workbench_obj.stop()


if __name__ == "__main__":
    locust.run_single_user(WorkbenchUser)
