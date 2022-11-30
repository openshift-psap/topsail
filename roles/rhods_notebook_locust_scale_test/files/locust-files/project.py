import json
import datetime
import time
import logging
import pathlib
import json

import jinja2

import common
from common import url_name

class Project(common.ContextBase):
    URL = "/api/k8s/apis/kubeflow.org/v1/namespaces/{namespace}/notebooks/{name}"

    def __init__(self, context):
        common.ContextBase.__init__(self, context)

        this_dir = pathlib.Path(__file__).absolute().parent
        with open(this_dir / "project.json") as f:
            self.template = f.read()

    def __call__(self, k8s_project):
        return ProjectObj(self.context, k8s_project)

    def create(self, name):
        project_tpl = jinja2.Template(self.template)
        project_rendered = project_tpl.render(dict(
            project_name=name,
        ))

        json.loads(project_rendered) # ensure that the JSON is valid

        project_request_url = "/api/k8s/apis/project.openshift.io/v1/projectrequests"
        k8s_obj = self.client.post(**url_name(project_request_url+"/{project_name}", project_name=name),
                         headers={"Content-Type": "application/json"},
                         data=project_rendered).json()

        return k8s_obj


class ProjectObj(common.ContextBase):
    def __init__(self, context, k8s_obj):
        common.ContextBase.__init__(self, context)
        self.k8s_obj = k8s_obj
