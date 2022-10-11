import json
import datetime
import time

class Notebook():
    def __init__(self, client, env, user_name):
        self.client = client
        self.env = env
        self.user_name = user_name

    def _get_image_tag(self):
        response = self.client.get("/api/images/jupyter")
        if response.status_code != 200:
            print(f"ERROR: GET images/jupyter --> {response.status_code}")
            return False

        for image in response.json():
            if image["name"] != self.env.NOTEBOOK_IMAGE_NAME: continue

            return image["tags"][0]["name"]

        print(f"ERROR: GET images/jupyter --> Couldn't find the image named '{image_name}'")
        return False


    def stop(self):
        if self.env.DO_NOT_STOP_NOTEBOOK:
            print("notebook.stop: NOOP")
            return

        self.client.patch("/api/notebooks",
                          headers={"Content-Type": "application/json"},
                          data=json.dumps(dict(state="stopped")))


    def create(self):
        image_tag = self._get_image_tag()

        notebook_data = {
            "notebookSizeName": self.env.NOTEBOOK_SIZE_NAME,
            "imageName": self.env.NOTEBOOK_IMAGE_NAME,
            "imageTagName": image_tag,
            "url": f"https://{self.env.DASHBOARD_HOST}",
            "gpus": 0,
            "envVars": {
                "configMap": {},
                "secrets": {}},
            "state":"started",
        }
        response = self.client.post("/api/notebooks",
                                    headers={"Content-Type": "application/json"},
                                    data=json.dumps(notebook_data))

        return response.json()

    def status(self, notebook_json):
        notebook_name = notebook_json["metadata"]["name"]
        namespace = notebook_json["metadata"]["namespace"]
        response = self.client.get(f"/api/notebooks/{self.env.NAMESPACE}/{notebook_name}/status")

        return response.json()

    def launch(self, first):
        notebook_json = self.create()

        start_time = datetime.datetime.now()
        start_ts = datetime.datetime.timestamp(start_time)
        TIMEOUT = datetime.timedelta(minutes=3)
        exception_msg = None
        count = 0
        print(f"Waiting for the Notebook {self.user_name} ...")
        while True:
            count += 1
            status = self.status(notebook_json)

            if status["isRunning"]:
                exception_msg = None
                print(f"Notebook {self.user_name} is running after {(datetime.datetime.now() - start_time)}.")
                break

            if (datetime.datetime.now() - start_time) > TIMEOUT:
                print(f"Timed out waiting for the notebook {self.user_name}")
                exception_msg = "Timed out"
                break

            time.sleep(1)

        finish_time = datetime.datetime.now()
        request_base = {
            "request_type": f"CREATE_{'FIRST_' if first else ''}NOTEBOOK",
            "response_time": (finish_time - start_time).total_seconds() * 1000,
            "name": f"Create_Notebook",
            "context": {"hello": "world"},
            "response": "no answer",
            "exception": exception_msg,
            "start_time": start_ts,
            "url": "/launch_a_notebook",
            "response_length": 0,
        }

        self.client.request_event.fire(**request_base)

        return notebook_json
