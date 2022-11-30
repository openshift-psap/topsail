import json
import logging

from bs4 import BeautifulSoup

import common
from common import url_name

class JupyterLab(common.ContextBase):
    def __init__(self, context, oauth):
        common.ContextBase.__init__(self, context)

        self.oauth = oauth

    def go_to_jupyterlab_page(self, k8s_workbench, workbench_route):
        try:
            base_url = k8s_workbench["metadata"]["annotations"]["ci-artifacts/base-url"]
        except KeyError:
            name = k8s_workbench["metadata"]["name"]
            namespace = k8s_workbench["metadata"]["namespace"]

            base_url = f"/notebook/{ namespace }/{ name }"

        full_base_url = f"https://{workbench_route}{base_url}"

        login_response = self.login_to_jupyterlab_page(full_base_url)
        if not login_response:
            return login_response

        return self.get_jupyterlab_page(full_base_url)

    @common.Step("Login to JupyterLab")
    def login_to_jupyterlab_page(self, base_url):
        needs_login = False
        with self.client.get(base_url, catch_response=True,
                             name="<jupyterlab_host>/{base_url} (login)") as response:

            if "Log in" in response.text:
                response.success()
                needs_login = True
                #if response.status_code != 403:
                #    logging.warning(f"Login to JupyterLab Page: response code is ({response.status_code}) but should have been 403")
            elif "<title>JupyterLab</title>" in response.text:
                # already logged in
                needs_login = False

            elif response.status_code == 503:
                raise ValueError("JupyterLab 503 error ...")

            elif response.status_code == 0:
                raise ValueError("JupyterLab empty response ...")

            else:
                common.debug_point()
                raise ValueError(f"JupyterLab authentication failed :/ (code {response.status_code})")

        if needs_login:
            login_response = self.oauth.do_login("JupyterLab", response)
            if not login_response:
                common.debug_point()
                raise ValueError(f"JupyterLab authentication failed .. (code {login_response.status_code})")

            final_response = login_response
        else:
            final_response = response

        return final_response

    @common.Step("Go to JupyterLab Page")
    def get_jupyterlab_page(self, base_url):
        response = self.client.get(base_url, name="<jupyterlab_host>/{base_url} (access)")
        if response.status_code == 0:
            raise ValueError("JupyterLab empty response ...")
        elif not response:
            common.debug_point()
            raise ValueError(f"JupyterLab home page failed to load ... (code {response.status_code})")

        soup = BeautifulSoup(response.text, features="lxml")
        if soup.title and soup.title.text == "JupyterLab":
            logging.info(f"Reached JupyterLab page \o/")

        elif soup.title and "Log in" in soup.title.text:
            common.debug_point()
            raise ValueError(f"JupyterLab home page failed to load properly... (still on the login page)")

        else:
            raise ValueError(f"JupyterLab home page failed to load properly... (unknown page, code {response.status_code})")


        return self.client.get(f"{base_url}/lab/api/workspaces",
                               name="<jupyterlab_host>/{base_url}/lab/api/workspaces")
