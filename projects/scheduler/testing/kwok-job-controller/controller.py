import kopf

@kopf.on.create('pod')
def pod_created(logger, **kwargs):
    # api = kubernetes.client.CoreV1Api()
    # obj = api.patch_namespaced_persistent_volume_claim(
    #     namespace=namespace,
    #     name=pvc_name,
    #     body=pvc_patch,
    # )
    logger.info(f"Pod created: {kwargs}")
