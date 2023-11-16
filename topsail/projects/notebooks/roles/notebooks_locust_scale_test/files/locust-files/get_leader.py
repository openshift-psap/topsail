import requests
import os
import urllib3
import logging
urllib3.disable_warnings()

def get_leader_ip():
    with open("/var/run/secrets/kubernetes.io/serviceaccount/token") as f:
        token = f.read()
    with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
        namespace = f.read()

    k8s_api = os.getenv("KUBERNETES_PORT").replace("tcp://", "https://")
    job_name = os.getenv("JOB_NAME")

    url = f"{k8s_api}/api/v1/namespaces/{namespace}/pods?labelSelector=job-name%3D{job_name}&limit=500"
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, headers=headers, verify=False)
    pod_list = response.json()

    if pod_list["kind"] != "PodList":
        logging.error("didn't receive a pod list :/ ", pod_list)
        exit(1)

    for pod in pod_list["items"]:
        try:
            index = pod["metadata"]["annotations"]["batch.kubernetes.io/job-completion-index"]
        except KeyError:
            continue
        if index != "0":
            continue
        try:
            return pod["status"]["podIP"]
        except KeyError:
            return False

    return None

if __name__ == "__main__":
    print(get_leadername())
