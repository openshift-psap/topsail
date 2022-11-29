import json
from bs4 import BeautifulSoup

class JupyterLab():
    def __init__(self, client, env, user_name, oauth):
        self.client = client
        self.env = env
        self.user_name = user_name
        self.oauth = oauth

    def get_jupyterlab_page(self):
        jupyterlab_host = self.env.DASHBOARD_HOST.replace("rhods-dashboard-redhat-ods-applications",
                                                          f"jupyter-nb-{self.user_name}-{self.env.NAMESPACE}")
        base_url = f"notebook/{self.env.NAMESPACE}/jupyter-nb-{self.user_name}/lab"

        response = self.client.get(f"{jupyterlab_host}/{base_url}")
        if f"Log in with" in response.text:
            response = self.oauth.do_login(response)

            if not response:
                return False

        soup = BeautifulSoup(response.text, features="lxml")
        print(f"Reached page '{soup.title}'")

        self.client.get(f"{jupyterlab_host}/{base_url}/api/workspaces",
                        name="/jupyterlab/api/workspaces")
