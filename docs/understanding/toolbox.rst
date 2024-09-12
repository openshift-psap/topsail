The Reusable Toolbox Layer
==========================

TOPSAIL's toolbox provides an extensive set of reusable
functionalities. It is a critical part of the test orchestration, as
the toolbox commands are in charge of the majority of the operations
affecting the state of the cluster.

The Ansible-based design of the toolbox has proved along the last
years to be a key element in the efficiency of TOPSAIL-based
performance and scale investigations.  The Ansible roles are always
executed locally, with a custom stdout callback for easy log reading.


In the design of toolbox framework, post-mortem troubleshooting is one
of the key concerns. The roles are always executed with a dedicated
artifact directory (``{{ artifact_extra_logs_dir }}``), when the tasks
are expected to store their generated source artifacts (``src``
directory), the state of the resources they have changed
(``artifacts`` directory). The role should also store any other
information helpful to understand why the role execution failed, as
well as any "proof" that it executed its task correctly. These
artifacts will be reviewed after the test execution, to understand
what went wrong, if the cluster was in the right state, etc. The
artifacts can also be parsed by the post-mortem visualization engine,
to extract test results, timing information, etc:

::

  - name: Create the src artifacts directory
    file:
      path: "{{ artifact_extra_logs_dir }}/src/"
      state: directory
      mode: '0755'

  - name: Create the nginx HTTPS route
    shell:
      set -o pipefail;
      oc create route passthrough nginx-secure
         --service=nginx --port=https
         -n "{{ cluster_deploy_nginx_server_namespace }}"
         --dry-run=client -oyaml
        | yq -y '.apiVersion = "route.openshift.io/v1"'
        | tee "{{ artifact_extra_logs_dir }}/src/route_nginx-secure.yaml"
        | oc apply -f -


  - name: Create the artifacts artifacts directory
    file:
      path: "{{ artifact_extra_logs_dir }}/artifacts/"
      state: directory
      mode: '0755'

  - name: Get the status of the Deployment and Pod
    shell:
      oc get deploy/nginx-deployment
         -owide
         -n "{{ cluster_deploy_nginx_server_namespace }}"
         > "{{ artifact_extra_logs_dir }}/artifacts/deployment.status";

      oc get pods -l app=nginx
         -owide
         -n "{{ cluster_deploy_nginx_server_namespace }}"
         > "{{ artifact_extra_logs_dir }}/artifacts/pod.status";

      oc describe pods -l app=nginx
         -n "{{ cluster_deploy_nginx_server_namespace }}"
         > "{{ artifact_extra_logs_dir }}/artifacts/pod.descr";

The commands are coded with Ansible roles, with a Python API and CLI
interface on top of it.

So this entrypoint:

::

    @AnsibleRole("cluster_deploy_nginx_server")
    @AnsibleMappedParams
    def deploy_nginx_server(self, namespace, directory):
        """
        Deploy an NGINX HTTP server

        Args:
            namespace: namespace where the server will be deployed. Will be create if it doesn't exist.
            directory: directory containing the files to serve on the HTTP server.
        """

will be translated into this CLI:

::

  $ ./run_toolbox.py cluster deploy_nginx_server --help

  INFO: Showing help with the command 'run_toolbox.py cluster deploy_nginx_server -- --help'.

  NAME
      run_toolbox.py cluster deploy_nginx_server - Deploy an NGINX HTTP server

  SYNOPSIS
      run_toolbox.py cluster deploy_nginx_server VALUE | NAMESPACE DIRECTORY

  DESCRIPTION
      Deploy an NGINX HTTP server

  POSITIONAL ARGUMENTS
      NAMESPACE
          namespace where the server will be deployed. Will be create if it doesn't exist.
      DIRECTORY
          directory containing the files to serve on the HTTP server.
