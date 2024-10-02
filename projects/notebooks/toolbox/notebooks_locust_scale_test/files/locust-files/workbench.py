import json
import datetime
import time
import logging
import pathlib
import json

import jinja2

import common
from common import url_name

LAUNCH_TIMEOUT = 3 # minutes

class Workbench(common.ContextBase):
    URL = "/api/k8s/apis/kubeflow.org/v1/namespaces/{namespace}/notebooks/{name}"

    def __init__(self, context):
        common.ContextBase.__init__(self, context)

        this_dir = pathlib.Path(__file__).absolute().parent
        with open(this_dir / "workbench.json") as f:
            self.template = f.read()

    def __call__(self, k8s_workbench):
        return WorkbenchObj(self.context, k8s_workbench)

    def create(self, k8s_project, name):
        project_name = k8s_project["metadata"]["name"]

        workbench_tpl = jinja2.Template(self.template)
        workbench_rendered = workbench_tpl.render(dict(
            name=name,
            namespace=project_name,
            dashboard_hostname=self.env.DASHBOARD_HOST,
        ))

        json.loads(workbench_rendered) # ensure that the JSON is valid

        response = self.client.post(
            **url_name(Workbench.URL, namespace=project_name, name=name),
            headers={"Content-Type": "application/json"},
            data=workbench_rendered)
        k8s_obj = common.check_status(response)

        if k8s_obj["kind"] == "Status":
            message = k8s_obj["message"]
            raise common.ScaleTestError(f"Could not create the workenbench '{name}' in project '{project_name}': {message}")

        return k8s_obj


class WorkbenchObj(common.ContextBase):
    def __init__(self, context, k8s_obj):
        common.ContextBase.__init__(self, context)
        self.k8s_obj = k8s_obj
        self.name = k8s_obj["metadata"]["name"] # may fail if namespace was being terminated

        self.namespace = k8s_obj["metadata"]["namespace"]
        self.url = url_name(Workbench.URL, namespace=self.namespace, name=self.name)

    def _get_image_tag(self):
        response = self.client.get("/api/images/jupyter")
        if response.status_code != 200:
            logging.error(f"GET images/jupyter --> {response.status_code}")
            return False

        for image in common.check_status(response):
            if image["name"] != self.env.NOTEBOOK_IMAGE_NAME: continue

            return image["tags"][0]["name"]

        logging.error(f"GET images/jupyter --> Couldn't find the image named '{image_name}'")
        return False


    def stop(self):
        if self.env.DO_NOT_STOP_NOTEBOOK:
            logging.info("notebook.stop: NOOP")
            return

        if self.is_stopped():
            self.is_stopped()
            logging.info(f"Workbench {self.namespace}/{self.name} already stopped")
            return
        logging.info(f"Stopping the workbench {self.namespace}/{self.name} ...")

        data = '[{"op":"add","path":"/metadata/annotations/kubeflow-resource-stopped","value":"stopped-by-topsail"}]'
        response = self.client.patch(**url_name(Workbench.URL, namespace=self.namespace, name=self.name, _descr="(stop)"),
                          headers={"Content-Type": "application/json"},
                                     data=data)
        self.k8s_obj = common.check_status(response)


    def is_stopped(self):
        return "kubeflow-resource-stopped" in self.k8s_obj["metadata"]["annotations"]

    def start(self):
        if not self.is_stopped():
            logging.info(f"Notebook {self.namespace}/{self.name} already started")
            return

        data = '[{"op":"remove","path":"/metadata/annotations/kubeflow-resource-stopped"}]'

        response = self.client.patch(**url_name(Workbench.URL, namespace=self.namespace, name=self.name, _descr="(start)"),
                                     headers={"Content-Type": "application/json"},
                                     data=data)
        self.k8s_obj = common.check_status(response)

    def wait(self):
        start_time = datetime.datetime.now()
        timeout = datetime.timedelta(minutes=LAUNCH_TIMEOUT)

        logging.info(f"Waiting for the Notebook {self.name} ...")

        meta_event = {
            "request_type": f"NOTEBOOK_LAUNCH",
            "name": f"notebook_ready",
            "response": "no answer",
            "url": "/launch",
            "response_length": 0,
            "exception": None,
            "user_name": self.user_name,
            "user_index": self.user_index,
        }
        with common.LocustMetaEvent(meta_event) as evt:
            route = None
            ready = False

            while True:
                if route is None:
                    route = self.get_route()
                    if route:
                        logging.info(f"Notebook {self.name} has a route after {(datetime.datetime.now() - start_time)}.")
                        evt.fire(dict(name="route_ready"))

                if not ready:
                    ready = self.is_ready()
                    if ready:
                        logging.info(f"Notebook {self.name} Pod is ready after {(datetime.datetime.now() - start_time)}.")
                        evt.fire(dict(name="pod_ready"))

                if ready and route:
                    break

                if (datetime.datetime.now() - start_time) > timeout:
                    logging.warning(f"Timed out waiting for the notebook {self.name}")
                    meta_event["exception"] = "Timed out"
                    break

                time.sleep(5)

        return route

    def delete(self):
        self.client.delete(self.url)

    def is_ready(self):
        response = self.client.get(**url_name("/api/k8s/api/v1/namespaces/{namespace}/pods", namespace=self.namespace, _query="labelSelector=notebook-name={workbench}"),
                                   params={"labelSelector": f"notebook-name={self.name}"})

        k8s_pods = common.check_status(response)["items"]
        if not k8s_pods:
            return None # Pod doesn't exist yet

        k8s_pod = k8s_pods[0]

        if k8s_pod["status"]["phase"] == "Pending":
            return False

        if not k8s_pod["status"].get("containerStatuses", []):
            return False

        ready = []
        for container_status in k8s_pod["status"]["containerStatuses"]:
            if not container_status.get("ready", False):
                return False
            if container_status.get("ready", False):
                ready.append(True)


        return ready and all(ready)

    def get_route(self):
        with self.client.get(
                **url_name("/api/k8s/apis/route.openshift.io/v1/namespaces/{namespace}/routes/{workbench_name}", namespace=self.namespace, workbench_name=self.name),
                catch_response=True) as response:
            if response.status_code == 404:
                response.success() # not an error, but the Route doesn't exist yet
                return False

        k8s_route = common.check_status(response)

        has_host = k8s_route["spec"].get("host")
        if not has_host:
            logging.warning(f"Route {workbench_name} exists but has no host :/")
            return False

        return k8s_route["spec"]["host"]
