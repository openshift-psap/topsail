
Toolbox Documentation
=====================
            

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

``container_bench``
*******************

::

    Commands relating to the performance evaluation
    

                
* :doc:`artifact_add_benchmark <Container_Bench.artifact_add_benchmark>`	 Runs the artifact add benchmark with the given runtime properties of exec_props: binary_path: path to the container engine binary (e.g., docker, podman) rootfull: whether to run the benchmark as root user additional_args: additional arguments to pass to the container engine binary exec_time_path: path to the exec_time.py script
* :doc:`capture_container_engine_info <Container_Bench.capture_container_engine_info>`	 Captures the info of the container engine
* :doc:`capture_system_state <Container_Bench.capture_system_state>`	 Captures the state of the remote Mac system
* :doc:`commit_container_benchmark <Container_Bench.commit_container_benchmark>`	 Runs the commit container benchmark with the given runtime properties of exec_props: binary_path: path to the container engine binary (e.g., docker, podman) rootfull: whether to run the benchmark as root user additional_args: additional arguments to pass to the container engine binary exec_time_path: path to the exec_time.py script
* :doc:`create_container_benchmark <Container_Bench.create_container_benchmark>`	 Runs the create benchmark with the given runtime properties of exec_props: binary_path: path to the container engine binary (e.g., docker, podman) rootfull: whether to run the benchmark as root user additional_args: additional arguments to pass to the container engine binary exec_time_path: path to the exec_time.py script
* :doc:`exec_container_benchmark <Container_Bench.exec_container_benchmark>`	 Runs the exec container benchmark with the given runtime properties of exec_props: binary_path: path to the container engine binary (e.g., docker, podman) rootfull: whether to run the benchmark as root user additional_args: additional arguments to pass to the container engine binary exec_time_path: path to the exec_time.py script
* :doc:`image_build_large_build_context_benchmark <Container_Bench.image_build_large_build_context_benchmark>`	 Runs the image build large build context benchmark with the given runtime properties of exec_props: binary_path: path to the container engine binary (e.g., docker, podman) rootfull: whether to run the benchmark as root user additional_args: additional arguments to pass to the container engine binary exec_time_path: path to the exec_time.py script
* :doc:`iperf_host_to_container_benchmark <Container_Bench.iperf_host_to_container_benchmark>`	 Runs the iperf3 benchmark from host to container with the given runtime properties of exec_props: binary_path: path to the container engine binary (e.g., docker, podman) rootfull: whether to run the benchmark as root user additional_args: additional arguments to pass to the container engine binary exec_time_path: path to the exec_time.py script
* :doc:`iperf_net_bridge_benchmark <Container_Bench.iperf_net_bridge_benchmark>`	 Runs the iperf3 benchmark using network bridge between containers with the given runtime properties of exec_props: binary_path: path to the container engine binary (e.g., docker, podman) rootfull: whether to run the benchmark as root user additional_args: additional arguments to pass to the container engine binary exec_time_path: path to the exec_time.py script
* :doc:`iperf_net_host_benchmark <Container_Bench.iperf_net_host_benchmark>`	 Runs the iperf3 benchmark using host network between containers with the given runtime properties of exec_props: binary_path: path to the container engine binary (e.g., docker, podman) rootfull: whether to run the benchmark as root user additional_args: additional arguments to pass to the container engine binary exec_time_path: path to the exec_time.py script
* :doc:`list_images_benchmark <Container_Bench.list_images_benchmark>`	 Runs the list images benchmark with the given runtime properties of exec_props: binary_path: path to the container engine binary (e.g., docker, podman) rootfull: whether to run the benchmark as root user additional_args: additional arguments to pass to the container engine binary exec_time_path: path to the exec_time.py script
* :doc:`load_image_benchmark <Container_Bench.load_image_benchmark>`	 Runs the load image benchmark with the given runtime properties of exec_props: binary_path: path to the container engine binary (e.g., docker, podman) rootfull: whether to run the benchmark as root user additional_args: additional arguments to pass to the container engine binary exec_time_path: path to the exec_time.py script
* :doc:`parallel_remove_image_benchmark <Container_Bench.parallel_remove_image_benchmark>`	 Runs the parallel remove image benchmark with the given runtime properties of exec_props: binary_path: path to the container engine binary (e.g., docker, podman) rootfull: whether to run the benchmark as root user additional_args: additional arguments to pass to the container engine binary exec_time_path: path to the exec_time.py script
* :doc:`prepare_benchmark_script_on_remote <Container_Bench.prepare_benchmark_script_on_remote>`	 Prepares the benchmark script on the remote machine
* :doc:`pull_image_benchmark <Container_Bench.pull_image_benchmark>`	 Runs the pull image benchmark with the given runtime properties of exec_props: binary_path: path to the container engine binary (e.g., docker, podman) rootfull: whether to run the benchmark as root user additional_args: additional arguments to pass to the container engine binary exec_time_path: path to the exec_time.py script
* :doc:`remove_container_benchmark <Container_Bench.remove_container_benchmark>`	 Runs the remove container benchmark with the given runtime properties of exec_props: binary_path: path to the container engine binary (e.g., docker, podman) rootfull: whether to run the benchmark as root user additional_args: additional arguments to pass to the container engine binary exec_time_path: path to the exec_time.py script
* :doc:`remove_image_benchmark <Container_Bench.remove_image_benchmark>`	 Runs the remove image benchmark with the given runtime properties of exec_props: binary_path: path to the container engine binary (e.g., docker, podman) rootfull: whether to run the benchmark as root user additional_args: additional arguments to pass to the container engine binary exec_time_path: path to the exec_time.py script
* :doc:`run_container_benchmark <Container_Bench.run_container_benchmark>`	 Runs the run container benchmark with the given runtime properties of exec_props: binary_path: path to the container engine binary (e.g., docker, podman) rootfull: whether to run the benchmark as root user additional_args: additional arguments to pass to the container engine binary exec_time_path: path to the exec_time.py script
* :doc:`save_image_benchmark <Container_Bench.save_image_benchmark>`	 Runs the save image benchmark with the given runtime properties of exec_props: binary_path: path to the container engine binary (e.g., docker, podman) rootfull: whether to run the benchmark as root user additional_args: additional arguments to pass to the container engine binary exec_time_path: path to the exec_time.py script
* :doc:`start_container_benchmark <Container_Bench.start_container_benchmark>`	 Runs the start benchmark with the given runtime properties of exec_props: binary_path: path to the container engine binary (e.g., docker, podman) rootfull: whether to run the benchmark as root user additional_args: additional arguments to pass to the container engine binary exec_time_path: path to the exec_time.py script
* :doc:`sysbench_cpu_benchmark <Container_Bench.sysbench_cpu_benchmark>`	 Runs the sysbench CPU benchmark with the given runtime properties of exec_props: binary_path: path to the container engine binary (e.g., docker, podman) rootfull: whether to run the benchmark as root user additional_args: additional arguments to pass to the container engine binary exec_time_path: path to the exec_time.py script
* :doc:`sysbench_fileio_container_benchmark <Container_Bench.sysbench_fileio_container_benchmark>`	 Runs the sysbench fileIO container benchmark with the given runtime properties of exec_props: binary_path: path to the container engine binary (e.g., docker, podman) rootfull: whether to run the benchmark as root user additional_args: additional arguments to pass to the container engine binary exec_time_path: path to the exec_time.py script
* :doc:`sysbench_fileio_mount_benchmark <Container_Bench.sysbench_fileio_mount_benchmark>`	 Runs the sysbench fileIO mount benchmark with the given runtime properties of exec_props: binary_path: path to the container engine binary (e.g., docker, podman) rootfull: whether to run the benchmark as root user additional_args: additional arguments to pass to the container engine binary exec_time_path: path to the exec_time.py script
* :doc:`sysbench_memory_read_benchmark <Container_Bench.sysbench_memory_read_benchmark>`	 Runs the sysbench memory read benchmark with the given runtime properties of exec_props: binary_path: path to the container engine binary (e.g., docker, podman) rootfull: whether to run the benchmark as root user additional_args: additional arguments to pass to the container engine binary exec_time_path: path to the exec_time.py script
* :doc:`sysbench_memory_write_benchmark <Container_Bench.sysbench_memory_write_benchmark>`	 Runs the sysbench memory write benchmark with the given runtime properties of exec_props: binary_path: path to the container engine binary (e.g., docker, podman) rootfull: whether to run the benchmark as root user additional_args: additional arguments to pass to the container engine binary exec_time_path: path to the exec_time.py script

``crc``
*******

::

    Commands relating to CRC
    

                
* :doc:`refresh_image <Crc.refresh_image>`	 Update a CRC AMI image with a given SNC repo commit

``fine_tuning``
***************

::

    Commands relating to RHOAI scheduler testing
    

                
* :doc:`ray_fine_tuning_job <Fine_Tuning.ray_fine_tuning_job>`	 Run a simple Ray fine-tuning Job.
* :doc:`run_fine_tuning_job <Fine_Tuning.run_fine_tuning_job>`	 Run a simple fine-tuning Job.

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

``jump_ci``
***********

::

    Commands to run TOPSAIL scripts in a jump host
    

                
* :doc:`ensure_lock <Jump_Ci.ensure_lock>`	 Ensure that cluster lock with a given name is taken. Fails otherwise.
* :doc:`prepare_step <Jump_Ci.prepare_step>`	 Prepares the jump host for running a CI test step:
* :doc:`prepare_topsail <Jump_Ci.prepare_topsail>`	 Prepares the jump host for running TOPSAIL: - clones TOPSAIL repository - builds TOPSAIL image in the remote host
* :doc:`release_lock <Jump_Ci.release_lock>`	 Release a cluster lock with a given name on a remote node
* :doc:`retrieve_artifacts <Jump_Ci.retrieve_artifacts>`	 Prepares the jump host for running a CI test step:
* :doc:`take_lock <Jump_Ci.take_lock>`	 Take a lock with a given cluster name on a remote node

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

``mac_ai``
**********

::

    Commands relating to the MacOS AI performance evaluation
    

                
* :doc:`remote_build_virglrenderer <Mac_Ai.remote_build_virglrenderer>`	 Builds the Virglrenderer library
* :doc:`remote_capture_cpu_ram_usage <Mac_Ai.remote_capture_cpu_ram_usage>`	 Captures the CPU and RAM usage on MacOS
* :doc:`remote_capture_power_usage <Mac_Ai.remote_capture_power_usage>`	 Captures the power usage on MacOS
* :doc:`remote_capture_system_state <Mac_Ai.remote_capture_system_state>`	 Captures the state of the remote Mac system
* :doc:`remote_capture_virtgpu_memory <Mac_Ai.remote_capture_virtgpu_memory>`	 Captures the virt-gpu memory usage
* :doc:`remote_llama_cpp_pull_model <Mac_Ai.remote_llama_cpp_pull_model>`	 Pulls a model with llama-cpp, on a remote host
* :doc:`remote_llama_cpp_run_bench <Mac_Ai.remote_llama_cpp_run_bench>`	 Benchmark a model with llama_cpp, on a remote host
* :doc:`remote_llama_cpp_run_model <Mac_Ai.remote_llama_cpp_run_model>`	 Runs a model with llama_cpp, on a remote host
* :doc:`remote_ollama_pull_model <Mac_Ai.remote_ollama_pull_model>`	 Pulls a model with ollama, on a remote host
* :doc:`remote_ollama_run_model <Mac_Ai.remote_ollama_run_model>`	 Runs a model with ollama, on a remote host
* :doc:`remote_ollama_start <Mac_Ai.remote_ollama_start>`	 Starts ollama, on a remote host
* :doc:`remote_ramalama_run_bench <Mac_Ai.remote_ramalama_run_bench>`	 Benchmark a model with ramalama, on a remote host
* :doc:`remote_ramalama_run_model <Mac_Ai.remote_ramalama_run_model>`	 Runs a model with ramalama, on a remote host

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

``pipelines``
*************

::

    Commands relating to RHODS
    

                
* :doc:`capture_notebooks_state <Pipelines.capture_notebooks_state>`	 Capture information about the cluster and the RHODS notebooks deployment
* :doc:`capture_state <Pipelines.capture_state>`	 Captures the state of a Data Science Pipeline Application in a given namespace.
* :doc:`deploy_application <Pipelines.deploy_application>`	 Deploy a Data Science Pipeline Application in a given namespace.
* :doc:`run_kfp_notebook <Pipelines.run_kfp_notebook>`	 Run a notebook in a given notebook image.

``remote``
**********

::

    Commands relating to the setup of remote hosts
    

                
* :doc:`build_image <Remote.build_image>`	 Builds a podman image
* :doc:`clone <Remote.clone>`	 Clones a Github repository in a remote host
* :doc:`download <Remote.download>`	 Downloads a file in a remote host
* :doc:`retrieve <Remote.retrieve>`	 Retrieves remote files locally

``repo``
********

::

    Commands to perform consistency validations on this repo itself
    

                
* :doc:`generate_ansible_default_settings <Repo.generate_ansible_default_settings>`	 Generate the `defaults/main/config.yml` file of the Ansible roles, based on the Python definition.
* :doc:`generate_middleware_ci_secret_boilerplate <Repo.generate_middleware_ci_secret_boilerplate>`	 Generate the boilerplace code to include a new secret in the Middleware CI configuration
* :doc:`generate_toolbox_related_files <Repo.generate_toolbox_related_files>`	 Generate the rst document and Ansible default settings, based on the Toolbox Python definition.
* :doc:`generate_toolbox_rst_documentation <Repo.generate_toolbox_rst_documentation>`	 Generate the `doc/toolbox.generated/*.rst` file, based on the Toolbox Python definition.
* :doc:`send_cpt_notification <Repo.send_cpt_notification>`	 Send a *CPT* notification to slack about the completion of a CPT job.
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
* :doc:`download_to_image <Storage.download_to_image>`	 Downloads the a dataset into an image in the internal registry
* :doc:`download_to_pvc <Storage.download_to_pvc>`	 Downloads the a dataset into a PVC of the cluster
