import matrix_benchmarking.models as matbench_models

from pydantic import Field

class PromValues(matbench_models.ExclusiveModel):
    Sutest_Control_Plane_Node_CPU_idle: matbench_models.PrometheusMetric = Field(
        ..., alias='Sutest Control Plane Node CPU idle'
    )
    Sutest_API_Server_Requests__server_errors_: matbench_models.PrometheusMetric = (
        Field(..., alias='Sutest API Server Requests (server errors)')
    )
    sutest__container_cpu__namespace_redhat_ods_applications_pod_rhods_dashboard___container_rhods_dashboard: matbench_models.PrometheusMetric = Field(
        ...,
        alias='sutest__container_cpu__namespace=redhat-ods-applications_pod=rhods-dashboard.*_container=rhods-dashboard',
    )
    sutest__container_sum_cpu__namespace_redhat_ods_applications_pod_rhods_dashboard___container_rhods_dashboard: matbench_models.PrometheusMetric = Field(
        ...,
        alias='sutest__container_sum_cpu__namespace=redhat-ods-applications_pod=rhods-dashboard.*_container=rhods-dashboard',
    )
    sutest__container_cpu_limits__namespace_redhat_ods_applications_pod_rhods_dashboard___container_rhods_dashboard: matbench_models.PrometheusMetric = Field(
        ...,
        alias='sutest__container_cpu_limits__namespace=redhat-ods-applications_pod=rhods-dashboard.*_container=rhods-dashboard',
    )
    sutest__container_cpu_requests__namespace_redhat_ods_applications_pod_rhods_dashboard___container_rhods_dashboard: matbench_models.PrometheusMetric = Field(
        ...,
        alias='sutest__container_cpu_requests__namespace=redhat-ods-applications_pod=rhods-dashboard.*_container=rhods-dashboard',
    )

    class Config:
        fields = {
            "Sutest_Control_Plane_Node_CPU_idle": "Sutest Control Plane Node CPU idle",
            "Sutest_API_Server_Requests__server_errors_": "Sutest API Server Requests (server errors)",
            "sutest__container_cpu__namespace_redhat_ods_applications_pod_rhods_dashboard___container_rhods_dashboard": 
                "sutest__container_cpu__namespace=redhat-ods-applications_pod=rhods-dashboard.*_container=rhods-dashboard",
            "sutest__container_sum_cpu__namespace_redhat_ods_applications_pod_rhods_dashboard___container_rhods_dashboard":
                "sutest__container_sum_cpu__namespace=redhat-ods-applications_pod=rhods-dashboard.*_container=rhods-dashboard",
            "sutest__container_cpu_limits__namespace_redhat_ods_applications_pod_rhods_dashboard___container_rhods_dashboard": 
                "sutest__container_cpu_limits__namespace=redhat-ods-applications_pod=rhods-dashboard.*_container=rhods-dashboard",
            "sutest__container_cpu_requests__namespace_redhat_ods_applications_pod_rhods_dashboard___container_rhods_dashboard": 
                "sutest__container_cpu_requests__namespace=redhat-ods-applications_pod=rhods-dashboard.*_container=rhods-dashboard"
        }
