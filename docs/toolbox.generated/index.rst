
Toolbox Documentation
=====================
            

``busy_cluster``
****************

::

    Commands relating to make a cluster busy with lot of resources
    

                
* :doc:`cleanup <Busy_Cluster.cleanup>`	 Cleanups namespaces to make a cluster un-busy
* :doc:`create_configmaps <Busy_Cluster.create_configmaps>`	 Creates configmaps and secrets to make a cluster busy
* :doc:`create_deployments <Busy_Cluster.create_deployments>`	 Creates configmaps and secrets to make a cluster busy
* :doc:`create_jobs <Busy_Cluster.create_jobs>`	 Creates jobs to make a cluster busy
* :doc:`create_namespaces <Busy_Cluster.create_namespaces>`	 Creates namespaces to make a cluster busy
* :doc:`status <Busy_Cluster.status>`	 Shows the busyness of the cluster

``cluster``
***********

::

    Commands relating to cluster scaling, upgrading and environment capture
    

                
* :doc:`build_push_image <Cluster.build_push_image>`	 Build and publish an image to quay using either a Dockerfile or git repo.
* :doc:`capture_environment <Cluster.capture_environment>`	 Captures the cluster environment
* :doc:`create_htpasswd_adminuser <Cluster.create_htpasswd_adminuser>`	 Create an htpasswd admin user.
* :doc:`create_osd <Cluster.create_osd>`	 Create an OpenShift Dedicated cluster.
* :doc:`deploy_operator <Cluster.deploy_operator>`	 Deploy an operator from OperatorHub catalog entry.
* :doc:`destroy_ocp <Cluster.destroy_ocp>`	 Destroy an OpenShift cluster
* :doc:`destroy_osd <Cluster.destroy_osd>`	 Destroy an OpenShift Dedicated cluster.
* :doc:`dump_prometheus_db <Cluster.dump_prometheus_db>`	 Dump Prometheus database into a file
* :doc:`fill_workernodes <Cluster.fill_workernodes>`	 Fills the worker nodes with place-holder Pods with the maximum available amount of a given resource name.
* :doc:`preload_image <Cluster.preload_image>`	 Preload a container image on all the nodes of a cluster.
* :doc:`query_prometheus_db <Cluster.query_prometheus_db>`	 Query Prometheus with a list of PromQueries read in a file
* :doc:`reset_prometheus_db <Cluster.reset_prometheus_db>`	 Resets Prometheus database, by destroying its Pod
* :doc:`set_project_annotation <Cluster.set_project_annotation>`	 Set an annotation on a given project, or for any new projects.
* :doc:`set_scale <Cluster.set_scale>`	 Ensures that the cluster has exactly `scale` nodes with instance_type `instance_type`
* :doc:`update_pods_per_node <Cluster.update_pods_per_node>`	 Update the maximum number of Pods per Nodes, and Pods per Core See alse: https://docs.openshift.com/container-platform/4.14/nodes/nodes/nodes-nodes-managing-max-pods.html
* :doc:`upgrade_to_image <Cluster.upgrade_to_image>`	 Upgrades the cluster to the given image
* :doc:`wait_fully_awake <Cluster.wait_fully_awake>`	 Waits for the cluster to be fully awake after Hive restart

``configure``
*************

::

    Commands relating to TOPSAIL testing configuration
    

                
* :doc:`apply <Configure.apply>`	 Applies a preset (or a list of presets) to the current configuration file
* :doc:`enter <Configure.enter>`	 Enter into a custom configuration file for a TOPSAIL project
* :doc:`get <Configure.get>`	 Gives the value of a given key, in the current configuration file
* :doc:`name <Configure.name>`	 Gives the name of the current configuration

``cpt``
*******

::

    Commands relating to continuous performance testing management
    

                
* :doc:`deploy_cpt_dashboard <Cpt.deploy_cpt_dashboard>`	 Deploy and configure the CPT Dashboard

``fine_tuning``
***************

::

    Commands relating to RHOAI scheduler testing
    

                
* :doc:`ray_fine_tuning_job <Fine_Tuning.ray_fine_tuning_job>`	 Run a simple Ray fine-tuning Job.
* :doc:`run_fine_tuning_job <Fine_Tuning.run_fine_tuning_job>`	 Run a simple fine-tuning Job.
* :doc:`run_quality_evaluation <Fine_Tuning.run_quality_evaluation>`	 Run a simple fine-tuning Job.

``run``
*******

::

    Run `topsail` toolbox commands from a single config file.
    

                

``gpu_operator``
****************

::

    Commands for deploying, building and testing the GPU operator in various ways
    

                
* :doc:`capture_deployment_state <Gpu_Operator.capture_deployment_state>`	 Captures the GPU operator deployment state
* :doc:`deploy_cluster_policy <Gpu_Operator.deploy_cluster_policy>`	 Creates the ClusterPolicy from the OLM ClusterServiceVersion
* :doc:`deploy_from_bundle <Gpu_Operator.deploy_from_bundle>`	 Deploys the GPU Operator from a bundle
* :doc:`deploy_from_operatorhub <Gpu_Operator.deploy_from_operatorhub>`	 Deploys the GPU operator from OperatorHub
* :doc:`enable_time_sharing <Gpu_Operator.enable_time_sharing>`	 Enable time-sharing in the GPU Operator ClusterPolicy
* :doc:`extend_metrics <Gpu_Operator.extend_metrics>`	 Enable time-sharing in the GPU Operator ClusterPolicy
* :doc:`get_csv_version <Gpu_Operator.get_csv_version>`	 Get the version of the GPU Operator currently installed from OLM Stores the version in the 'ARTIFACT_EXTRA_LOGS_DIR' artifacts directory.
* :doc:`run_gpu_burn <Gpu_Operator.run_gpu_burn>`	 Runs the GPU burn on the cluster
* :doc:`undeploy_from_operatorhub <Gpu_Operator.undeploy_from_operatorhub>`	 Undeploys a GPU-operator that was deployed from OperatorHub
* :doc:`wait_deployment <Gpu_Operator.wait_deployment>`	 Waits for the GPU operator to deploy
* :doc:`wait_stack_deployed <Gpu_Operator.wait_stack_deployed>`	 Waits for the GPU Operator stack to be deployed on the GPU nodes

``kepler``
**********

::

    Commands relating to kepler deployment
    

                
* :doc:`deploy_kepler <Kepler.deploy_kepler>`	 Deploy the Kepler operator and monitor to track energy consumption
* :doc:`undeploy_kepler <Kepler.undeploy_kepler>`	 Cleanup the Kepler operator and associated resources

``kserve``
**********

::

    Commands relating to RHOAI KServe component
    

                
* :doc:`capture_operators_state <Kserve.capture_operators_state>`	 Captures the state of the operators of the KServe serving stack
* :doc:`capture_state <Kserve.capture_state>`	 Captures the state of the KServe stack in a given namespace
* :doc:`deploy_model <Kserve.deploy_model>`	 Deploy a KServe model
* :doc:`extract_protos <Kserve.extract_protos>`	 Extracts the protos of an inference service
* :doc:`extract_protos_grpcurl <Kserve.extract_protos_grpcurl>`	 Extracts the protos of an inference service, with GRPCurl observe
* :doc:`undeploy_model <Kserve.undeploy_model>`	 Undeploy a KServe model
* :doc:`validate_model <Kserve.validate_model>`	 Validate the proper deployment of a KServe model

``kubemark``
************

::

    Commands relating to kubemark deployment
    

                
* :doc:`deploy_capi_provider <Kubemark.deploy_capi_provider>`	 Deploy the Kubemark Cluster-API provider
* :doc:`deploy_nodes <Kubemark.deploy_nodes>`	 Deploy a set of Kubemark nodes

``kwok``
********

::

    Commands relating to KWOK deployment
    

                
* :doc:`deploy_kwok_controller <Kwok.deploy_kwok_controller>`	 Deploy the KWOK hollow node provider
* :doc:`set_scale <Kwok.set_scale>`	 Deploy a set of KWOK nodes

``llm_load_test``
*****************

::

    Commands relating to llm-load-test
    

                
* :doc:`run <Llm_Load_Test.run>`	 Load test the wisdom model

``local_ci``
************

::

    Commands to run the CI scripts in a container environment similar to the one used by the CI
    

                
* :doc:`run <Local_Ci.run>`	 Runs a given CI command
* :doc:`run_multi <Local_Ci.run_multi>`	 Runs a given CI command in parallel from multiple Pods

``nfd``
*******

::

    Commands for NFD related tasks
    

                
* :doc:`has_gpu_nodes <Nfd.has_gpu_nodes>`	 Checks if the cluster has GPU nodes
* :doc:`has_labels <Nfd.has_labels>`	 Checks if the cluster has NFD labels
* :doc:`wait_gpu_nodes <Nfd.wait_gpu_nodes>`	 Wait until nfd find GPU nodes
* :doc:`wait_labels <Nfd.wait_labels>`	 Wait until nfd labels the nodes

``nfd_operator``
****************

::

    Commands for deploying, building and testing the NFD operator in various ways
    

                
* :doc:`deploy_from_operatorhub <Nfd_Operator.deploy_from_operatorhub>`	 Deploys the NFD Operator from OperatorHub
* :doc:`undeploy_from_operatorhub <Nfd_Operator.undeploy_from_operatorhub>`	 Undeploys an NFD-operator that was deployed from OperatorHub

``notebooks``
*************

::

    Commands relating to RHOAI Notebooks
    

                
* :doc:`benchmark_performance <Notebooks.benchmark_performance>`	 Benchmark the performance of a notebook image.
* :doc:`capture_state <Notebooks.capture_state>`	 Capture information about the cluster and the RHODS notebooks deployment
* :doc:`cleanup <Notebooks.cleanup>`	 Clean up the resources created along with the notebooks, during the scale tests.
* :doc:`dashboard_scale_test <Notebooks.dashboard_scale_test>`	 End-to-end scale testing of ROAI dashboard scale test, at user level.
* :doc:`locust_scale_test <Notebooks.locust_scale_test>`	 End-to-end testing of RHOAI notebooks at scale, at API level
* :doc:`ods_ci_scale_test <Notebooks.ods_ci_scale_test>`	 End-to-end scale testing of ROAI notebooks, at user level.

``pipelines``
*************

::

    Commands relating to RHODS
    

                
* :doc:`capture_state <Pipelines.capture_state>`	 Captures the state of a Data Science Pipeline Application in a given namespace.
* :doc:`deploy_application <Pipelines.deploy_application>`	 Deploy a Data Science Pipeline Application in a given namespace.
* :doc:`run_kfp_notebook <Pipelines.run_kfp_notebook>`	 Run a notebook in a given notebook image.

``repo``
********

::

    Commands to perform consistency validations on this repo itself
    

                
* :doc:`generate_ansible_default_settings <Repo.generate_ansible_default_settings>`	 Generate the `defaults/main/config.yml` file of the Ansible roles, based on the Python definition.
* :doc:`generate_middleware_ci_secret_boilerplate <Repo.generate_middleware_ci_secret_boilerplate>`	 Generate the boilerplace code to include a new secret in the Middleware CI configuration
* :doc:`generate_toolbox_related_files <Repo.generate_toolbox_related_files>`	 Generate the rst document and Ansible default settings, based on the Toolbox Python definition.
* :doc:`generate_toolbox_rst_documentation <Repo.generate_toolbox_rst_documentation>`	 Generate the `doc/toolbox.generated/*.rst` file, based on the Toolbox Python definition.
* :doc:`send_job_completion_notification <Repo.send_job_completion_notification>`	 Send a *job completion* notification to github and/or slack about the completion of a test job.
* :doc:`validate_no_broken_link <Repo.validate_no_broken_link>`	 Ensure that all the symlinks point to a file
* :doc:`validate_no_wip <Repo.validate_no_wip>`	 Ensures that none of the commits have the WIP flag in their message title.
* :doc:`validate_role_files <Repo.validate_role_files>`	 Ensures that all the Ansible variables defining a filepath (`project/*/toolbox/`) do point to an existing file.
* :doc:`validate_role_vars_used <Repo.validate_role_vars_used>`	 Ensure that all the Ansible variables defined are actually used in their role (with an exception for symlinks)

``rhods``
*********

::

    Commands relating to RHODS
    

                
* :doc:`capture_state <Rhods.capture_state>`	 Captures the state of the RHOAI deployment
* :doc:`delete_ods <Rhods.delete_ods>`	 Forces ODS operator deletion
* :doc:`deploy_addon <Rhods.deploy_addon>`	 Installs the RHODS OCM addon
* :doc:`deploy_ods <Rhods.deploy_ods>`	 Deploy ODS operator from its custom catalog
* :doc:`dump_prometheus_db <Rhods.dump_prometheus_db>`	 Dump Prometheus database into a file
* :doc:`reset_prometheus_db <Rhods.reset_prometheus_db>`	 Resets RHODS Prometheus database, by destroying its Pod.
* :doc:`undeploy_ods <Rhods.undeploy_ods>`	 Undeploy ODS operator
* :doc:`update_datasciencecluster <Rhods.update_datasciencecluster>`	 Update RHOAI datasciencecluster resource
* :doc:`wait_odh <Rhods.wait_odh>`	 Wait for ODH to finish its deployment
* :doc:`wait_ods <Rhods.wait_ods>`	 Wait for ODS to finish its deployment

``scheduler``
*************

::

    Commands relating to RHOAI scheduler testing
    

                
* :doc:`cleanup <Scheduler.cleanup>`	 Clean up the scheduler load namespace
* :doc:`create_mcad_canary <Scheduler.create_mcad_canary>`	 Create a canary for MCAD Appwrappers and track the time it takes to be scheduled
* :doc:`deploy_mcad_from_helm <Scheduler.deploy_mcad_from_helm>`	 Deploys MCAD from helm
* :doc:`generate_load <Scheduler.generate_load>`	 Generate scheduler load

``server``
**********

::

    Commands relating to the deployment of servers on OpenShift
    

                
* :doc:`deploy_ldap <Server.deploy_ldap>`	 Deploy OpenLDAP and LDAP Oauth
* :doc:`deploy_minio_s3_server <Server.deploy_minio_s3_server>`	 Deploy Minio S3 server
* :doc:`deploy_nginx_server <Server.deploy_nginx_server>`	 Deploy an NGINX HTTP server
* :doc:`deploy_opensearch <Server.deploy_opensearch>`	 Deploy OpenSearch and OpenSearch-Dashboards
* :doc:`deploy_redis_server <Server.deploy_redis_server>`	 Deploy a redis server
* :doc:`undeploy_ldap <Server.undeploy_ldap>`	 Undeploy OpenLDAP and LDAP Oauth

``storage``
***********

::

    Commands relating to OpenShift file storage
    

                
* :doc:`deploy_aws_efs <Storage.deploy_aws_efs>`	 Deploy AWS EFS CSI driver and configure AWS accordingly.
* :doc:`deploy_nfs_provisioner <Storage.deploy_nfs_provisioner>`	 Deploy NFS Provisioner
* :doc:`download_to_pvc <Storage.download_to_pvc>`	 Downloads the a dataset into a PVC of the cluster
