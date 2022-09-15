import gevent
import time
import datetime
import os
import pickle
import json

import locust
import locust_plugins
from locust import HttpUser, task
from bs4 import BeautifulSoup

from locust_plugins.users import HttpUserWithResources
from locust.exception import StopUser

import urllib3
import urllib3.util.url
urllib3.disable_warnings()

DASHBOARD_HOST = os.getenv("ODH_DASHBOARD_URL")
USERNAME_PREFIX = os.getenv("TEST_USERS_USERNAME_PREFIX")
JOB_COMPLETION_INDEX = os.getenv("JOB_COMPLETION_INDEX", 0)
IDP_NAME = os.getenv("TEST_USERS_IDP_NAME")
creds_file = os.getenv("CREDS_FILE")
NAMESPACE = "rhods-notebooks"

NOTEBOOK_IMAGE_NAME = os.getenv("NOTEBOOK_IMAGE_NAME")

SAVE_COOKIES = False

# Other env variables:
# - PGUSER # timescaledb username
# - LOCUST_USERS (number of users)
# - LOCUST_RUN_TIME (locust test duration)
# - LOCUST_SPAWN_RATE (locust number of new users per seconds)
# - LOCUST_LOCUSTFILE (locustfile.py file that will be executed)

class Notebook():
    def __init__(self, client, user_name):
        self.user_name = user_name
        self.data = {}
        self.client = client

    def _get_data(self, kind, purpose, template=None):
        fname = f"{kind}_{purpose}.json"
        try: return self.data[fname]
        except KeyError: pass

        with open(fname) as f:
            data = f.read()

        for key, value in (dict(user_name=self.user_name)|(template or {})).items():
            data = data.replace(f"{{{key}}}", str(value))

        json_data = self.data[fname] = json.loads(data)

        return json_data

    def get_or_create(self, kind, purpose, template=None, namespace_in_post=False):
        data = self._get_data(kind, purpose, template)

        endpoint = f"/api/{kind}/{NAMESPACE}"

        name = data['metadata']['name']
        print(f"[{purpose}] GET {kind}/{name}")
        with self.client.get(f"{endpoint}/{name}",
                             catch_response=True, name=endpoint) as response:

            is_not_found = (
                response.status_code == 404 or
                response.status_code == 200 and response.text == "null")

            if is_not_found:
                response.success()

                print(f"[{purpose}] POST {kind}/{name}")
                endpoint = f"/api/{kind}"
                if namespace_in_post:
                    endpoint += f"/{NAMESPACE}"

                response = self.client.post(endpoint, headers={"Content-Type": "application/json"},
                                 data=json.dumps(data))

                if response.status_code != 200:
                    print(f"ERROR: [{purpose}] POST {kind}/{name} --> {response.status_code}")
                    import pdb;pdb.set_trace()
                    return False

            elif response.status_code == 200:
                pass # resource exists
            else:
                print(f"ERROR: [{purpose}] GET {kind}/{name} --> {response.status_code}")
                import pdb;pdb.set_trace()
                return False

        return response

    def get(self, kind, purpose, modifier=None):
        data = self._get_data(kind, purpose)
        name = data['metadata']['name']

        print(f"[{purpose}] GET {kind}/{name}")
        endpoint_name = f"/api/{kind}/{NAMESPACE}"
        endpoint = f"/api/{kind}/{NAMESPACE}/{name}"
        if modifier:
            endpoint_name += f"/{modifier}"
            endpoint += f"/{modifier}"

        return self.client.get(endpoint, name=endpoint_name)

    def patch_object(self, kind, obj):
        name = obj['metadata']['name']

        print(f"PATCH {kind}/{name}")
        endpoint = f"/api/{kind}/{NAMESPACE}"
        return self.client.patch(f"{endpoint}/{name}", name=endpoint,
                                 headers={"Content-Type": "application/json"},
                                 data=json.dumps(obj))

    def patch(self, kind, purpose, action):
        purpose_data = self._get_data(kind, purpose)
        action_data = self._get_data(kind, action)
        name = purpose_data['metadata']['name']

        print(f"[{purpose}/{action}] PATCH {kind}/{name}")
        endpoint = f"/api/{kind}/{NAMESPACE}"
        return self.client.patch(f"{endpoint}/{name}", name=endpoint,
                                 headers={"Content-Type": "application/json"},
                                 data=json.dumps(action_data))

    def get_image(self):
        response = self.client.get("/api/images/jupyter")
        if response.status_code != 200:
            print(f"ERROR: GET images/jupyter --> {response.status_code}")
            return False

        for image in response.json():
            if image["name"] != NOTEBOOK_IMAGE_NAME: continue

            return image["dockerImageRepo"] + ":" + image["tags"][0]["name"]

        print(f"ERROR: GET images/jupyter --> Couldn't find the image named '{NOTEBOOK_IMAGE_NAME}'")
        return False

USER_PASSWORD = None
with open(creds_file) as f:
    for line in f:
        if not line.startswith("user_password="): continue
        USER_PASSWORD = line.strip().split("=")[1]

class RhodsUser(HttpUser):
    host = DASHBOARD_HOST
    verify = False
    user_next_id = 50
    default_resource_filter = f'/A(?!{DASHBOARD_HOST}/data:image:)'
    bundle_resource_stats = False

    def do_login(self, response):
        if "Log in with OpenShift" in response.text:
            response = self.do_login_with_openshift(response)
            if response is False:
                return False

        response = self.do_login_with(response, IDP_NAME)
        if response is False:
            return False

        response = self.do_log_in_to_your_account(response, self.user_name, USER_PASSWORD)
        if response is False:
            return False

        if "Authorize" in response.text:
            response = self.do_authorize_service_account(response)
            if response is False:
                return False

        return response

    def do_login_with_openshift(self, response):
        print("Log in with OpenShift")
        #
        # Page: Log in with OpenShift
        #
        soup = BeautifulSoup(response.text, features="lxml")
        action = soup.body.find("form").get("action")

        return self.client.get(action, params={"rd":"/"}, name=action)

    def do_login_with(self, response, method):
        print("Log in with ...")
        #
        # Page: Log in with ...
        #
        url = urllib3.util.url.parse_url(response.url)
        oauth_host = f"{url.scheme}://{url.netloc}"

        soup = BeautifulSoup(response.text, features="lxml")
        for auth_type in soup.find_all("a"):
            if auth_type.text != method: continue
            action = auth_type.get("href")
            break
        else:
            print("FAILED")
            return False

        return self.client.get(oauth_host + action, name=action.partition("?")[0])


    def do_log_in_to_your_account(self, response, username, password):
        print("Log in to your account")
        #
        # Page: Log in to your account
        #
        soup = BeautifulSoup(response.text, features="lxml")
        form = soup.body.find("form")
        action = form.get("action")

        url = urllib3.util.url.parse_url(response.url)
        oauth_host = f"{url.scheme}://{url.netloc}"

        params = {}
        for form_input in form.find_all("input"):
            if form_input.get("type") == "hidden":
                params[form_input.get("name")] = form_input.get("value")

        with self.client.post(oauth_host + action, data=params|{
            "username": username,
            "password": password,
        }, catch_response=True) as response:
            soup = BeautifulSoup(response.text, features="lxml")

            if "Log in" in str(soup.title):
                print("Authentication failed")
                response.failure("Authentication failed")
                return False

        return response

    def do_authorize_service_account(self, response):
        print("Authorize ...")
        #
        # Authorize ...
        #

        url = urllib3.util.url.parse_url(response.url)
        oauth_host = f"{url.scheme}://{url.netloc}"
        next_url = oauth_host + url.path

        soup = BeautifulSoup(response.text, features="lxml")

        action = soup.find("form").get("action")
        params = {}
        form = soup.body.find("form")
        for form_input in form.find_all("input"):
            name = form_input.get("name")
            value = form_input.get("value")
            if form_input.get("type") == "hidden":
                params[name] = value
                continue

            if form_input.get("type") == "checkbox":
                if name not in params:
                    params[name] = []
                params[name].append(value)
                continue

            if form_input.get("type") == "submit" and name == "approve":
                params[name] = value
                continue

        next_response = self.client.post(next_url, data=params)

        return next_response

    def on_start(self):
        self.client.verify = False

        self.loop = 0
        self.user_id = self.__class__.user_next_id
        self.user_name = f"{USERNAME_PREFIX}{self.user_id}"
        self.__class__.user_next_id += 1
        print(f"Running user #{self.user_name}")

        if SAVE_COOKIES:
            try:
                with open(f"cookies.{self.user_id}.pickle", "rb") as f:
                    self.client.cookies.update(pickle.load(f))
            except FileNotFoundError: pass # ignore
            except EOFError: pass # ignore

        if not self.go_to_rhods_dashboard():
            print("Failed to go to RHODS dashboard")
            return False

        if SAVE_COOKIES:
            with open(f"cookies.{self.user_id}.pickle", "wb") as f:
                pickle.dump(self.client.cookies, f)

    def go_to_rhods_dashboard(self):
        print("get_rhods_dashboard")
        self.client.verify = False

        with self.client.get("/", catch_response=True) as response:
            if response.status_code == 403:
                response.success()

                response = self.do_login(response)
                if not response:
                    return False

        return response

    #@task
    def get_rhods_dashboard_elements(self):
        print("get_rhods_dashboard_elements")

        self.client.get("/api/builds")
        self.client.get("/api/config")
        self.client.get("/api/status")
        self.client.get("/api/segment-key")
        self.client.get("/api/console-links")
        self.client.get("/api/quickstarts")
        self.client.get("/api/components", params={"installed":"true"})
        pass

    #@task
    def get_jupyter_spawner_elements(self):
        print("get_jupyter_spawner_elements")

        self.client.get("/api/images/jupyter")
        self.client.get("/api/rolebindings/redhat-ods-applications/rhods-notebooks-image-pullers")
        self.client.get("/api/gpu")

        pass

    #@task
    def get_assets_elements(self):
        print("get_assets_elements")

        self.client.get("5.bundle.css")
        self.client.get("/rhods-favicon.svg")
        self.client.get("/rhods-logo.svg")
        self.client.get("/jupyter.svg")
        self.client.get("/CheckStar.svg")
        self.client.get("/app.css")
        self.client.get("/app.bundle.js")

        for idx in 0, 1, 2, 3:
            self.client.get(f"/{idx}.bundle.css")
        for idx in 0, 1, 2, 3, 9:
            self.client.get(f"/{idx}.bundle.js")

    #@task
    def get_jupyterlab_page(self):
        JUPYTERLAB_HOST = DASHBOARD_HOST.replace("rhods-dashboard-redhat-ods-applications", f"jupyter-nb-{self.user_name}-{NAMESPACE}")
        BASE_URL = f"notebook/{NAMESPACE}/jupyter-nb-{self.user_name}/lab"

        response = self.client.get(f"{JUPYTERLAB_HOST}/{BASE_URL}")
        if f"Log in with" in response.text:
            response = self.do_login(response)
        soup = BeautifulSoup(response.text, features="lxml")
        print(f"Reached page '{soup.title}'")

        self.client.get(f"{JUPYTERLAB_HOST}/{BASE_URL}/api/workspaces", name="/jupyterlab/api/workspaces")


    @task
    def launch_a_notebook(self):
        print("launch_a_notebook")
        if __name__ == "__main__" and self.loop != 0:
            raise StopUser()
        self.notebook = notebook = Notebook(self.client, self.user_name)

        image = notebook.get_image()
        if not image: return False

        notebook_template = dict(
            dashboard_url=DASHBOARD_HOST,
            notebook_image=image,
        )

        notebook._get_data("notebooks", "jupyterlab", template=notebook_template)

        notebook.patch("notebooks", "jupyterlab", "terminate")

        if not notebook.get_or_create("pvc", "storage"): return False
        if not notebook.get_or_create("configmaps", "envs"): return False
        if not notebook.get_or_create("secrets", "envs"): return False

        notebook_resp = notebook.get_or_create("notebooks", "jupyterlab",
                                              template=notebook_template,
                                              namespace_in_post=True)
        if not notebook_resp:
            return False

        notebook_json = notebook_resp.json()

        # if the notebook is running, stop it
        if notebook_json.get("status") and notebook_json["status"]["readyReplicas"] != 0:
            notebook_resp = notebook.patch("notebooks", "jupyterlab", "terminate")

            while notebook_resp.json()["status"]["readyReplicas"] != 0:
                time.sleep(1)
                notebook_resp = notebook.get("notebooks", "jupyterlab")
                if notebook_resp.status_code != 200:
                    print(f"ERROR: failed to refresh the notebook state: {notebook_resp.status_code}")
                    return False

            # the notebook is stopped

        # if the notebook is stopped, restart it
        if notebook_json["metadata"]["annotations"].get("kubeflow-resource-stopped"):
            notebook_resp = notebook.get("notebooks", "jupyterlab")
            notebook_json = notebook_resp.json()
            notebook_json["metadata"]["annotations"]["kubeflow-resource-stopped"] = None

            resp = notebook.patch_object("notebooks", notebook_json)
            if resp.status_code != 200:
                print(f"ERROR: failed to restart the notebook: {resp.status_code}")
                return False

            print("Notebook was stopped")

        start_time = datetime.datetime.now()
        start_ts = datetime.datetime.timestamp(start_time)
        TIMEOUT = 3*60 # 3 minutes
        exception_msg = None
        count = 0
        print(f"Waiting for the Notebook {notebook.user_name} ...")
        while True:
            count += 1
            #self.client.get(f"/api/nb-events/rhods-notebooks/jupyter-{notebook.user_name}")
            endpoint = "/api/notebooks/rhods-notebooks"
            response = notebook.get("notebooks", "jupyterlab", modifier="status")

            if response.status_code != 200:
                print(f"An error happened when getting info about the notebook {notebook.user_name}", response)
                time.sleep(1)
                exception_msg = f"Error {response.status_code}"
                break

            response_json = response.json()

            if response_json["isRunning"]:
                exception_msg = None
                print(f"Notebook {notebook.user_name} is running after {count} seconds.")
                break

            if count > TIMEOUT:
                print(f"Timed out waiting for the notebook {notebook.user_name}")
                exception_msg = "Timed out"
                break

            time.sleep(1)

        self.get_jupyterlab_page()

        finish_time = datetime.datetime.now()
        request_base = {
            "request_type": f"CREATE_{'FIRST_' if self.loop == 0 else ''}NOTEBOOK",
            "response_time": (finish_time - start_time).total_seconds() * 1000,
            "name": f"Create_Notebook",
            "context": {"hello": "world"},
            "response": "no answer",
            "exception": exception_msg,
            "start_time": start_ts,
            "url": "/launch_a_notebook",
            "response_length": 0,
        }
        self.loop += 1
        self.client.request_event.fire(**request_base)

        notebook.patch("notebooks", "jupyterlab", "terminate")
        if __name__ == "__main__":
            raise StopUser()

    def on_stop(self):
        self.notebook.patch("notebooks", "jupyterlab", "terminate")
        pass

if __name__ == "__main__":
    locust.run_single_user(RhodsUser)
