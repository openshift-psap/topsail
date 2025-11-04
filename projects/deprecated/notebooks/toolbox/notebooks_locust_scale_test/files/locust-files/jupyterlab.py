import json
import logging
import time
import datetime

from bs4 import BeautifulSoup

import common
from common import url_name

class JupyterLab(common.ContextBase):
    def __init__(self, context, oauth):
        common.ContextBase.__init__(self, context)

        self.oauth = oauth

    def go_to_jupyterlab_page(self, workbench_obj, workbench_route):
        k8s_workbench = workbench_obj.k8s_obj
        try:
            base_url = k8s_workbench["metadata"]["annotations"]["topsail/base-url"]
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
        failed = False
        MAX_RETRIES = 5
        RETRY_DELAY = 1 # seconds
        try_count = 0
        while True:
            try_count += 1
            with self.client.get(base_url, catch_response=True,
                                 name="<jupyterlab_host>/{base_url} (login)") as response:
                err_kwargs = {}
                if "Log in" in response.text:
                    response.success()
                    needs_login = True
                    #if response.status_code != 403:
                    #    logging.warning(f"Login to JupyterLab Page: response code is ({response.status_code}) but should have been 403")
                elif "<title>JupyterLab</title>" in response.text:
                    # already logged in
                    needs_login = False

                elif response.status_code == 503:
                    failed = "JupyterLab 503 error ..."
                    err_kwargs = dict(known_bug="RHODS-5912")
                    common.bug_hit("RHODS-5912", self.user_name)
                elif response.status_code == 0:
                    failed = "JupyterLab empty response ... (during login)"
                    err_kwargs = dict(known_bug="RHODS-6126")
                    common.bug_hit("RHODS-6126", self.user_name, "login")
                else:
                    common.debug_point()
                    failed = f"JupyterLab authentication failed :/ (code {response.status_code})"
                    err_kwargs = dict(unclear=True)

                if failed:
                    response.failure(failed)

            if failed:
                if try_count == MAX_RETRIES:
                    raise common.ScaleTestError(failed, **err_kwargs)
                else:
                    time.sleep(RETRY_DELAY)
            else:
                break

        if needs_login:
            login_response = self.oauth.do_login(response)
            if not login_response:
                raise common.ScaleTestError(f"JupyterLab authentication failed .. (code {login_response.status_code})", unclear=True)

            final_response = login_response
        else:
            final_response = response

        return final_response

    @common.Step("Go to JupyterLab Page")
    def get_jupyterlab_page(self, base_url):
        MAX_RETRIES = 5
        RETRY_DELAY = 1 # seconds
        try_count = 0
        while True:
            try_count += 1
            response = self.client.get(base_url, name="<jupyterlab_host>/{base_url} (access)")
            if response.status_code == 0:
                common.bug_hit("RHODS-6126", self.user_name, "access")

                if try_count == MAX_RETRIES:
                    raise common.ScaleTestError(f"JupyterLab empty response ... (during access, tried {try_count} times)", known_bug="RHODS-6126")
                time.sleep(RETRY_DELAY)
                continue

            if not response:
                raise common.ScaleTestError(f"JupyterLab home page failed to load ... (code {response.status_code})",
                                            unclear=True)
            break

        soup = BeautifulSoup(response.text, features="lxml")
        if soup.title and soup.title.text == "JupyterLab":
            logging.info(f"Reached JupyterLab page \\o/")

        elif soup.title and "Log in" in soup.title.text:
            raise common.ScaleTestError(f"JupyterLab home page failed to load properly... (still on the login page)",
                                        unclear=True)

        else:
            raise common.ScaleTestError(f"JupyterLab home page failed to load properly... (unknown page, code {response.status_code})")


        return self.client.get(f"{base_url}/lab/api/workspaces",
                               name="<jupyterlab_host>/{base_url}/lab/api/workspaces")
