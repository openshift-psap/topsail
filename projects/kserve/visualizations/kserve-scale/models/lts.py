from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field

import matrix_benchmarking.models as matbench_models


class Metadata(matbench_models.Metadata):
    presets: List[str]
    config: Any
    ocp_version: matbench_models.SemVer
    rhoai_version: matbench_models.SemVer

    number_of_inferenceservices_to_create: int
    number_of_inferenceservice_per_user: int
    number_of_users: int


class Metrics(matbench_models.ExclusiveModel):
    serving_runtime_istio_proxy_container_cpu_usage: matbench_models.PrometheusValues = \
        Field(..., alias="sutest__container_cpu__namespace=kserve.*_container=istio-proxy")
    kserve_controller_cpu_usage: matbench_models.PrometheusValues = \
        Field(..., alias="sutest__container_cpu__namespace=redhat-ods-applications_pod=kserve-controller-manager-.*")
    kserve_controller_memory_usage: matbench_models.PrometheusValues = \
        Field(..., alias="sutest__container_memory_usage_bytes__namespace=redhat-ods-applications_pod=kserve-controller-manager-.*")
    istio_egress_cpu_usage: matbench_models.PrometheusValues = \
        Field(..., alias="sutest__container_cpu__namespace=istio-system_pod=istio-egressgateway-.*")
    istio_egress_memory_usage: matbench_models.PrometheusValues = \
        Field(..., alias="sutest__container_memory_usage_bytes__namespace=istio-system_pod=istio-egressgateway-.*")
    istio_ingress_cpu_usage: matbench_models.PrometheusValues = \
        Field(..., alias="sutest__container_cpu__namespace=istio-system_pod=istio-ingressgateway-.*")
    istio_ingress_memory_usage: matbench_models.PrometheusValues = \
        Field(..., alias="sutest__container_memory_usage_bytes__namespace=istio-system_pod=istio-ingressgateway-.*")

    istio_istiod_cpu_usage: matbench_models.PrometheusValues = \
        Field(..., alias="sutest__container_cpu__namespace=istio-system_pod=istiod-data-science-smcp-.*")
    istio_ingress_memory_usage: matbench_models.PrometheusValues = \
        Field(..., alias="sutest__container_memory_usage_bytes__namespace=istio-system_pod=istiod-data-science-smcp-.*")

    knative_activator_cpu_usage: matbench_models.PrometheusValues = \
        Field(..., alias="sutest__container_cpu__namespace=knative-serving_pod=activator-.*")
    knative_activator_memory_usage: matbench_models.PrometheusValues = \
        Field(..., alias="sutest__container_memory_usage_bytes__namespace=knative-serving_pod=activator-.*")



class Results(matbench_models.ExclusiveModel):
    inferenceservice_load_times: List[float]
    number_of_inferenceservices_loaded: int
    number_of_successful_users: int
    test_duration: float

    metrics: Metrics


class Payload(matbench_models.ExclusiveModel):
    metadata: Metadata
    results: Results
