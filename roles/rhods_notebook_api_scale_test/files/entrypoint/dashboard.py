import json
from bs4 import BeautifulSoup

class Dashboard():
    def __init__(self, client, env, user_name, oauth):
        self.client = client
        self.env = env
        self.user_name = user_name
        self.oauth = oauth

    def go_to_dashboard(self):
        print("get_rhods_dashboard")

        with self.client.get("/", catch_response=True) as response:
            if response.status_code == 403:
                response.success()

                response = self.oauth.do_login(response)
                if not response:
                    return False

        return response

    def get_dashboard_elements(self):
        print("get_rhods_dashboard_elements")

        self.client.get("/api/builds")
        self.client.get("/api/config")
        self.client.get("/api/status")
        self.client.get("/api/segment-key")
        self.client.get("/api/console-links")
        self.client.get("/api/quickstarts")
        self.client.get("/api/components", params={"installed":"true"})
        pass

    def get_jupyter_spawner_elements(self):
        print("get_jupyter_spawner_elements")

        self.client.get("/api/images/jupyter")
        self.client.get("/api/rolebindings/redhat-ods-applications/rhods-notebooks-image-pullers")
        self.client.get("/api/gpu")

        pass

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
