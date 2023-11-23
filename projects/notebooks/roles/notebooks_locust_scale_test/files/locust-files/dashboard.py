import json
import pathlib
import logging

from bs4 import BeautifulSoup

import common
import project
import workbench

from common import url_name

class Dashboard(common.ContextBase):
    PROJECTS_URL = "/api/k8s/apis/project.openshift.io/v1/projects"
    CORE_URL = "/api/k8s/api/v1/namespaces"
    NOTEBOOKS_URL = "/api/k8s/apis/kubeflow.org/v1/namespaces/{namespace}/notebooks"

    def __init__(self, context, oauth):
        common.ContextBase.__init__(self, context)

        self.oauth = oauth
        self.project = project.Project(context)
        self.workbench = workbench.Workbench(context)

    @common.Step("Login to Dashboard")
    def connect_to_the_dashboard(self):
        failed = False
        with self.client.get("/", catch_response=True) as response:
            if response.status_code == 403:
                response.success()

                response = self.oauth.do_login(response)
                if not response:
                    failed = f"Dashboard authentication failed ... (code {response.status_code})"
                    response.failure(failed)

        if failed:
            raise common.ScaleTestError(failed, unclear=True)

        return response

    @common.Step("Fetch the RHODS Dashboard frontend")
    def fetch_the_dashboard_frontend(self):
        if not self.env.SKIP_OPTIONAL:
            self.client.get("/app.bundle.js")
            self.client.get("/app.bundle.css")
            self.client.get("/app.css")
            self.client.get("/rhods-favicon.svg")

    @common.Step("Load RHODS Dashboard")
    def load_the_dashboard(self):
        if not self.env.SKIP_OPTIONAL:
            self.client.get("/") # HTML page

            self.client.get("/api/builds")
            self.client.get("/api/config")
            self.client.get("/api/status")
            self.client.get("/api/segment-key")
            self.client.get("/api/console-links")
            self.client.get("/api/quickstarts")
            self.client.get("/api/components", params={"installed":"true"})

    @common.Step("Go to the Project page")
    def go_to_the_project_page(self, project_name):
        k8s_project = self.get_or_create_the_project(project_name)

        k8s_workbenches = self._go_to_the_project_page(project_name)

        return k8s_project, k8s_workbenches

    def get_or_create_the_project(self, project_name):
        if not self.env.SKIP_OPTIONAL:
            self.client.get("/projects") # HTML page
            self.client.get("/api/status")

        response = self.client.get(**url_name(Dashboard.PROJECTS_URL,
                                              _query="labelSelector=opendatahub.io/dashboard=true"),
                                   params={"labelSelector": "opendatahub.io/dashboard=true"})
        k8s_projects = common.check_status(response)

        k8s_project = self._get_k8s_obj_from_list(k8s_projects, project_name)
        if not k8s_project:
            logging.info(f"Create project {project_name}")
            k8s_project = self.project.create(project_name)
        else:
            try:
                if k8s_project["status"]["phase"] == "Terminating":
                    raise RuntimeError(f"Project {project_name} is being terminated ...")
            except KeyError: pass

            logging.info(f"Project {project_name} already exists")

        return k8s_project

    def _go_to_the_project_page(self, project_name):
        if not self.env.SKIP_OPTIONAL:
            self.client.get(**url_name("/projects/{project_name}", project_name=project_name)) # HTML page

            self.client.get(**url_name(Dashboard.PROJECTS_URL+"/{project_name}", project_name=project_name))

        # Workbenches
        response = self.client.get(**url_name(Dashboard.NOTEBOOKS_URL, namespace=project_name))
        k8s_workbenches = common.check_status(response)

        if not self.env.SKIP_OPTIONAL:
            # Cluster storage
            self.client.get(**url_name(Dashboard.CORE_URL+"/{project_name}/persistentvolumeclaims", project_name=project_name))

            # Data connections
            self.client.get(**url_name(Dashboard.CORE_URL+"/{project_name}/secrets", project_name=project_name),
                            params={"labelSelector": "opendatahub.io/managed=true"})

        return k8s_workbenches

    @common.Step("Create and Start the Workbench")
    def create_and_start_the_workbench(self, k8s_project, k8s_workbenches, workbench_name):
        k8s_workbench = self._get_k8s_obj_from_list(k8s_workbenches, workbench_name)

        if k8s_workbench:
            workbench_obj = self.workbench(k8s_workbench)
            if not workbench_obj.is_stopped():
                logging.info(f"Workbench {workbench_name} was running, stop it.")

                workbench_obj.stop()

            workbench_obj.start()
        else:
            workbench_obj = self.workbench(self.workbench.create(k8s_project, workbench_name))

        route = workbench_obj.wait()

        return workbench_obj, route

    def _get_k8s_obj_from_list(self, k8s_list, name):
        for item in k8s_list["items"]:
            if item["metadata"]["name"] == name:
                return item

        return None
