Creating a New Orchestration
============================

You're working on a new perf&scale test project, and you want to have
it automated and running in the CI? Good! Do you already have you test
architecture in mind? And your toolbox is ready? Perfect, so we can
start building the orchestration!

Prepare the environment
-----------------------

To create an orchestration, go to ``projects/PROJECT_NAME/testing``
and prepare the following boilerplate code.

Mind that the ``PROJECT_NAME`` should be compatible with Python
packages (no ``-``) to keep things simple.


Prepare the ``test.py``, ``config.yaml`` and ``command_args.yaml.j2``
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

These files are all what is mandatory to have a configurable
orchestration layer.

* ``test.py`` should contain these entrypoints, for interacting with the CI:

::

  @entrypoint()
  def prepare_ci():
      """
      Prepares the cluster and the namespace for running the tests
      """

      pass


  @entrypoint()
  def test_ci():
      """
      Runs the test from the CI
      """

      pass


  @entrypoint()
  def cleanup_cluster(mute=False):
      """
      Restores the cluster to its original state
      """
      # _Not_ executed in OpenShift CI cluster (running on AWS). Only required for running in bare-metal environments.

      common.cleanup_cluster()

      pass


  @entrypoint(ignore_secret_path=True, apply_preset_from_pr_args=False)
  def generate_plots_from_pr_args():
      """
      Generates the visualization reports from the PR arguments
      """

      visualize.download_and_generate_visualizations()

      export.export_artifacts(env.ARTIFACT_DIR, test_step="plot")


  class Entrypoint:
      """
      Commands for launching the CI tests
      """

      def __init__(self):

          self.prepare_ci = prepare_ci
          self.test_ci = test_ci
          self.cleanup_cluster_ci = cleanup_cluster
          self.export_artifacts = export_artifacts

          self.generate_plots_from_pr_args = generate_plots_from_pr_args

  def main():
      # Print help rather than opening a pager
      fire.core.Display = lambda lines, out: print(*lines, file=out)

      fire.Fire(Entrypoint())


  if __name__ == "__main__":
      try:
          sys.exit(main())
      except subprocess.CalledProcessError as e:
          logging.error(f"Command '{e.cmd}' failed --> {e.returncode}")
          sys.exit(1)
      except KeyboardInterrupt:
          print() # empty line after ^C
          logging.error(f"Interrupted.")
          sys.exit(1)

* ``config.yaml`` should contain

::

  ci_presets:
    # name of the presets to apply, or null if no preset
    name: null
    # list of names of the presets to apply, or a single name, or null if no preset
    names: null


    single:
      clusters.create.type: single

    keep:
      clusters.create.keep: true
      clusters.create.ocp.tags.Project: PSAP/Project/...
      # clusters.create.ocp.tags.TicketId:

    light_cluster:
      clusters.create.ocp.deploy_cluster.target: cluster_light

    light:
      extends: [light_cluster]
      ...

    ...

  secrets:
    dir:
      name: psap-ods-secret
      env_key: PSAP_ODS_SECRET_PATH
    # name of the file containing the properties of LDAP secrets
    s3_ldap_password_file: s3_ldap.passwords
    keep_cluster_password_file: get_cluster.password
    brew_registry_redhat_io_token_file: brew.registry.redhat.io.token
    opensearch_instances: opensearch.yaml
    aws_credentials: .awscred
    git_credentials: git-credentials

  clusters:
    metal_profiles:
      ...: ...
    create:
      type: single # can be: single, ocp, managed
      keep: false
      name_prefix: fine-tuning-ci
      ocp:
        # list of tags to apply to the machineset when creating the cluster
        tags:
          # TicketId: "..."
          Project: PSAP/Project/...
        deploy_cluster:
          target: cluster
        base_domain: psap.aws.rhperfscale.org
        version: 4.15.9
        region: us-west-2
        control_plane:
          type: m6a.xlarge
        workers:
          type: m6a.2xlarge
          count: 2

    sutest:
      is_metal: false
      lab:
        name: null
      compute:
        dedicated: true
        machineset:
          name: workload-pods
          type: m6i.2xlarge
          count: null
          taint:
            key: only-workload-pods
            value: "yes"
            effect: NoSchedule
    driver:
      is_metal: false
      compute:
        dedicated: true
        machineset:
          name: test-pods
          count: null
          type: m6i.2xlarge
          taint:
            key: only-test-pods
            value: "yes"
            effect: NoSchedule
    cleanup_on_exit: false

  matbench:
    preset: null
    workload: projects....visualizations...
    prom_workload: projects....visualizations....
    config_file: plots.yaml
    download:
      mode: prefer_cache
      url:
      url_file:
      # if true, copy the results downloaded by `matbench download` into the artifacts directory
      save_to_artifacts: false
    # directory to plot. Set by testing/common/visualize.py before launching the visualization
    test_directory: null
    lts:
      generate: true
      horreum:
        test_name: null
      opensearch:
        export:
          enabled: false
          enabled_on_replot: false
          fail_test_on_fail: true
        instance: smoke
        index: ...
        index_prefix: ""
        prom_index_suffix: -prom
      regression_analyses:
        enabled: false
        # if the regression analyses fail, mark the test as failed
        fail_test_on_regression: false
  export_artifacts:
    enabled: false
    bucket: rhoai-cpt-artifacts
    path_prefix: cpt/fine-tuning
    dest: null # will be set by the export code

* ``command_args.yml.j2`` should start with:

::

  {% set secrets_location = false | or_env(secrets.dir.env_key) %}
  {% if not secrets_location %}
    {{ ("ERROR: secrets_location must be defined (secrets.dir.name="+ secrets.dir.name|string +" or env(secrets.dir.env_key=" + secrets.dir.env_key|string + ")) ") | raise_exception }}
  {% endif %}
  {% set s3_ldap_password_location = secrets_location + "/" + secrets.s3_ldap_password_file %}

  # ---


Copy the ``clusters.sh`` and ``configure.sh``
"""""""""""""""""""""""""""""""""""""""""""""

These files are necessary to be able to create clusters on
OpenShift CI. (``/test rhoai-e2e``). They shouldn't be modified.

And now, the boiler-plate code is in place, and we can start building
the test orchestration.

Create ``test_....py`` and ``prepare_....py``
"""""""""""""""""""""""""""""""""""""""""""""

Starting at this step, the development of the test orchestration
starts, and you "just" have to fill the gaps :)


In the ``prepare_ci`` method, prepare your cluster, according to the
configuration. In the ``test_ci`` method, run your test and collect
its artifacts. In the ``cleanup_cluster_ci``, cleanup you cluster, so
that it can be used again for another test.

Start building your test orchestration
--------------------------------------

One the boilerplate code is in place, we can start building the test
orchestration. TOPSAIL provides some "low level" helper modules:

::

  from projects.core.library import env, config, run, configure_logging, export

as well as libraries of common orchestration bits:

::

  from projects.rhods.library import prepare_rhoai as prepare_rhoai_mod
  from projects.gpu_operator.library import prepare_gpu_operator
  from projects.matrix_benchmarking.library import visualize


These libraries are illustrated below. They are not formally described
at the moment. They come from project code blocks that have noticed to
be used identically across projects, so they have been moved to
library directories to be easier to reuse.

Sharing code across projects means extending the risk of unnoticed
bugs when updating the library. With this in mind, the question of
code sharing vs code duplication takes another direction, as extensive
testing is not easy in such a rapidly evolving project.


Core helper modules
"""""""""""""""""""

The ``run`` module
''''''''''''''''''

* helper functions to run system commands, toolbox commands, and
  ``from_config`` toolbox commands:

::

   def run(command, capture_stdout=False, capture_stderr=False, check=True, protect_shell=True, cwd=None, stdin_file=None, log_command=True)

This method allows running a command, capturing or not its
stdout/stderr, checking it's return code, chaning it's working
directory, protecting it with bash safety flags (``set -o
errexit;set -o pipefail;set -o nounset;set -o errtrace``), passing a
file as stdin, logging or not the command, ...

::

   def run_toolbox(group, command, artifact_dir_suffix=None, run_kwargs=None, mute_stdout=None, check=None, **kwargs)

This command allows running a toolbox command. ``group, command,
kwargs`` are the CLI toolbox command arguments.  ``run_kwargs`` allows
passing arguments directory to the ``run`` command described
above. ``mute_stdout`` allows muting (capturing) the stdout
text. ``check`` allows disabling the exception on error
check. ``artifact_dir_suffix`` allows appending a suffix to the
toolbox directory name (eg, to distinguish two identical calls in the
artifacts).

::

   def run_toolbox_from_config(group, command, prefix=None, suffix=None, show_args=None, extra=None, artifact_dir_suffix=None, mute_stdout=False, check=True, run_kwargs=None)

This command allows running a toolbox command with the ``from_config``
helper (see the description of the ``command_args.yaml.j2``
file). ``prefix`` and ``suffix`` allow distinguishing commands in the
``command_args.yaml.j2`` file. ``extra`` allows passing extra
arguments that override what is in the template file. ``show_args``
only display the arguments that would be passed to ``run_toolbox.py``.z

* ``run_and_catch`` is an helper function for chaining multiple
  functions without swallowing exceptions:

::

    exc = None
    exc = run.run_and_catch(
      exc,
      run.run_toolbox, "kserve", "capture_operators_state", run_kwargs=dict(capture_stdout=True),
    )

    exc = run.run_and_catch(
      exc,
      run.run_toolbox, "cluster", "capture_environment", run_kwargs=dict(capture_stdout=True),
    )

    if exc: raise exc

* helper context to run functions in parallel. If
  ``exit_on_exception`` is set, the code will exit the process when an
  exception is catch. Otherwise it will simply raise it. If
  ``dedicated_dir`` is set, a dedicated directly, based on the
  ``name`` parameter, will be created.

::

    class Parallel(object):
        def __init__(self, name, exit_on_exception=True, dedicated_dir=True):

Example:

::

    def prepare():
      with run.Parallel("prepare1") as parallel:
          parallel.delayed(prepare_rhoai)
          parallel.delayed(scale_up_sutest)


      test_settings = config.project.get_config("tests.fine_tuning.test_settings")
      with run.Parallel("prepare2") as parallel:
          parallel.delayed(prepare_gpu)
          parallel.delayed(prepare_namespace, test_settings)

      with run.Parallel("prepare3") as parallel:
          parallel.delayed(preload_image_yyy)
          parallel.delayed(preload_image_xxx)
          parallel.delayed(preload_image_zzz)


The ``env`` module
''''''''''''''''''

* ``ARTIFACT_DIR`` thread-safe access to the storage directory. Prefer
  using this than ``$ARTIFACT_DIR`` which isn't thread safe.

* helper context to create a dedicated artifact directory. Based on
  OpenShift CI, TOPSAIL relies on the ``ARTIFACT_DIR`` environment
  variable to store its artifacts. Each toolbox command creates a new
  directory name ``nnn__group__command``, which keeps the directories
  ordered and easy to follow. However, when many commands are executed,
  sometimes in parallel, the number of directories increase and becomes
  hard to understand. This command allows creating subdirectories, to
  group things logically:

Example:

::

    with env.NextArtifactDir("prepare_namespace"):
        set_namespace_annotations()
        download_data_sources(test_settings)

The ``config`` module
'''''''''''''''''''''

* the ``config.project.get_config(<config key>)`` helper command to
  access the configuration. Uses the inline Json format.  This object
  holds the main project configuration.

* the ``config.project.set_config(<config key>, <value>)`` helper
  command to update the configuration. Sometimes, it is convenient to
  store values in the configuration (eg, coming from the
  command-line). Mind that this is not thread-safe (an error is raised
  if this command is called in a ``run.Parallel`` context). Mind that
  this command does not allow creating new configuration fields in the
  document. Only existing fields can be updated.


The ``projects.rhods.library.prepare_rhoai`` library module
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

This library helps with the deployment of RHOAI pre-builds on OpenShift.

* ``install_servicemesh()`` installs the ServiceMesh Operator, if not
  already installed in the cluster (this is a dependency of RHOAI)

* ``uninstall_servicemesh(mute=True)`` uninstall the ServiceMesh
  Operator, if it is installed

* ``is_rhoai_installed()`` tells if RHOAI is currently installed or
  not.

* ``install(token_file=None, force=False)`` installs RHOAI, if it is
  not already installed (unless ``force`` is passed). Mind that the
  current deployment code only works with the pre-builds of RHOAI,
  which require a Brew ``token_file``. If the token isn't passed, it
  is assumed that the cluster already has access to Brew.


The ``projects.gpu_operator.library.prepare_gpu_operator`` library module
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

This library helps with the deployment of the GPU stack on OpenShift.

* ``prepare_gpu_operator()`` deploys the NFD Operator and the GPU
  Operator, if they are not already installed.

* ``wait_ready(...)`` waits for the GPU Operator stack to be deployed,
  and optionally enable additional GPU Operator features:

    * ``enable_time_sharing`` enables the time-sharing capability of
      the GPU Operator, (configured via the ``command_args.yaml.j2``
      file).
    * ``extend_metrics=True, wait_metrics=True`` enables extra metrics
      to be captured by the GPU Operator DCGM component (the
      "well-known" metrics set). If ``wait_metrics`` is enabled, the
      automation will wait for the DCGM to start reporting these
      metrics.
    * ``wait_stack_deployed`` allows disabling the final wait, and
      only enable the components above.

* ``cleanup_gpu_operator()`` undeploys the GPU Operator and the NFD
  Operator, if they are deployed.

* ``add_toleration(effect, key)`` adds a toleration to the GPU
  Operator DaemonSet Pods. This allows the GPU Operator Pods to be
  deployed on nodes with specific taints. Mind that this command
  overrides any toleration previously set.

The ``projects.local_ci.library.prepare_user_pods`` library module
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

This library helps with the execution of multi-user TOPSAIL tests.

Multi-user tests consist in Pods running inside the cluster, and
all executing a TOPSAIL command. Their initialization is synchronized
with a barrier, then they wait a configurable delay before starting
their script. When they terminate, their file artifacts are collected via a
S3 server, and stored locally for post-processing.

* ``prepare_base_image_container(namespace)`` builds a TOPSAIL image
  in a given namespace. The image must be consistent with the commit
  of TOPSAIL being tested, so the ``BuildConfig`` relies on the PR
  number of fetch the right commit. The ``apply_prefer_pr`` function
  provides the helper code to update the configuration with the number
  of the PR being tested.

* ``apply_prefer_pr(pr_number=None)`` inspects the environment to
  detect the PR number. When running locally, export
  ``HOMELAB_CI=true`` and ``PULL_NUMBER=...`` for this function to
  automatically detect the PR number. Mind that this function updates
  the configuration file, so it cannot run inside a parallel context.

* ``delete_istags(namespace)`` cleanups up the istags used by TOPSAIL
  User Pods.

* ``rebuild_driver_image(namespace, pr_number)`` helps refreshing the
  image when running locally.

::

    @entrypoint()
    def rebuild_driver_image(pr_number):
        namespace = config.project.get_config("base_image.namespace")
        prepare_user_pods.rebuild_driver_image(namespace, pr_number)

* ``cluster_scale_up(user_count)`` scales up the cluster with the
  right number of nodes (when not running in a bare-metal cluster).

* ``prepare_user_pods(user_count)`` prepares the cluster for running a
  multi-user scale test. Deploys the dependency tools (minio, redis),
  builds the image, prepare the ServiceAccount that TOPSAIL will use,
  prepare the secrets that TOPSAIL will have access to ...

* ``cleanup_cluster()`` cleanups up the cluster by deleting the User
  Pod namespace.

The ``projects.matrix_benchmarking.library.visualize`` library module
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

This module helps with the post-processing of TOPSAIL results.

* ``prepare_matbench()`` is called from the ContainerFile. It
  installs the ``pip`` dependencies of MatrixBenchmarking.

* ``download_and_generate_visualizations(results_dirname)`` is called
  from the CIs, when replotting. It downloads test results runs the
  post-processing steps against it.

* ``generate_from_dir(results_dirname, generate_lts=None)`` is the
  main entrypoint of this library. It accepts a directory as argument,
  and runs the post-processing steps against it. The expected
  configuration should be further documented ...
