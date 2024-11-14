The Test Orchestrations Layer
=============================

The test orchestration layer is the crux of TOPSAIL. It binds
everything else together:
- the CI job launchers
- the configuration
- the toolbox commands
- the post-mortem visualizations and automated regression analyses.

Historically, this layer has been first and foremost triggered by CI
jobs, with clean clusters and kube-admin privileges. This is still the
first target of TOPSAIL test automation. The side effect of that is
that TOPSAIL may seem not very user-friendly when trying to use it
interactively from a terminal.

In this section, we'll try to cover these different aspects that
TOPSAIL binds together.

The CI job launchers
====================

TOPSAIL test orchestrations are focused on reproducibility and
end-to-end testing. These two ideas are directly linked, and in the
OpenShift world, the easiest to ensure that the rests are reproducible
and end-to-end automated is to start from scratch (or from a fresh and
clean cluster).

Cluster creation
^^^^^^^^^^^^^^^^

In OpenShift CI, TOPSAIL has the ability to create a dedicated cluster
(even two, one for RHOAI, one for simulating users). This mode is
launched with the ``rhoai-e2e`` test. It is particularly useful when
launching cloud scale tests. The cluster creation is handled by the
`deploy-cluster subproject
<https://github.com/openshift-psap/topsail/tree/main/projects/cluster/subprojects/deploy-cluster>`_.
This part of TOPSAIL is old, and mostly written in Bash. But it has
proved to be robust and reliable, although we haven't been using it
much since we got access to bare-metal clusters.

By default, these clusters are destroyed after the test.
A ``keep`` flag can be set in the configuration to avoid destroying
it, and creating a kube-admin user with a predefined password. (Ask
in PM for how access the cluster).

Cluster from pool
^^^^^^^^^^^^^^^^^

In OpenShift CI, TOPSAIL has a pool of pre-deployed clusters. These
clusters are controlled by the `Hive
<https://www.redhat.com/en/blog/openshift-hive-cluster-as-a-service>`_
tool, managed by the OpenShift CI team. In the current configuration,
the pool have 2 single-node OpenShift systems.

These clusters are always destroyed at the end of the run. This is
outside of TOPSAIL control.

Bare-metal clusters
^^^^^^^^^^^^^^^^^^^

In the Middleware Jenkins CI, TOPSAIL can be launched against two
bare-metal clusters. These clusters have long running OpenShift
deployments, and they are "never" reinstalled (at least, there is no
reinstall automation in place at the moment). Hence, the test
orchestrations are in charge of cleanup the cluster before (to ensure
that no garbage is left) and after the test (to let the cluster clean
for the following users). So the complete test sequence is:

1. cleanup
2. prepare
3. test
4. cleanup

This is the theory at least. In practice, the clusters are dedicated
to the team, and after mutual agreement, the cleanups and prepare
steps may be skipped to save time. Or the test and final cleanup, to
have a cluster ready for development.

Before launching a test, check the state of the cluster. Is RHOAI
installed? is the DSC configured as you expected? If not, make sure
you tick the cleanup and prepare steps.

Is someone else's job already on the same cluster? if yes, your job
will be queued and start only after the first job completion. Make
sure you tick the cleanup and prepare steps.

Launching TOPSAIL jobs on the CI engines
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

See this google doc for all the details about launching TOPSAIL jobs
on the CI engines:

* `How to launch TOPSAIL tests <https://docs.google.com/document/d/1uBL294crnFVnaRdBEtP4_qHIBadojQl3Ccc8VNpmCNQ/edit?usp=sharing>`_

TOPSAIL Configuration System
============================

The configuration system is (yet another) key element of TOPSAIL. It
has been designed to flexible, modular, and (important point to
understand some of its implementation choices) configurable from
OpenShift CI and other CI engines.

A bit of history
^^^^^^^^^^^^^^^^

OpenShift CI is a great tool, but a strong limitation of it is that it
can be only statically configured (from the `openshift/release
<https://github.com/openshift/release/tree/master/ci-operator/config/openshift-psap/topsail>`_
repository). TOPSAIL had to find a way to enable dynamic
configuration, without touching the source code. Long story (see a
small `slide deck
<https://docs.google.com/presentation/d/1DxULqo8U3jRZqUU52xEL8JnfGzV_IE_sSjGKJsZNTTU/edit?usp=sharing>`_
illustrating it) short, TOPSAIL can be configured in Github. (See `How
to launch TOPSAIL tests
<https://docs.google.com/document/d/1uBL294crnFVnaRdBEtP4_qHIBadojQl3Ccc8VNpmCNQ/edit?usp=sharing>`_
for all the details).

::

    /test rhoai-light fine_tuning ibm_40gb_models
    /var tests.fine_tuning.test_settings.gpu: [2, 4]


A bit of apology
^^^^^^^^^^^^^^^^

TOPSAIL project's configuration is a YAML document.  On one side, each
project is free to define is own configuration. But on the other side,
some code is shared between different projects (the ``library`` files,
defined in some of the projects).

This aspect (the full flexibility + the code reuse in the libraries)
makes the configuration structure hard to track. A refactoring might
be envisaged to have a more strongly defined configuration format, at
least for the reusable libraries (eg, the library could tell: this
configuration block does not follow my model, I do not accept to
process it).

How it actually works
^^^^^^^^^^^^^^^^^^^^^

So, TOPSAIL project's configuration is a YAML document. And the test
orchestration reads it alter its behavior. It's as simple as that.

::

  tests:
    capture_prom: true
    capture_state: true

::

    capture_prom = config.project.get_config("tests.capture_prom")
    if not capture_prom:
        logging.info("tests.capture_prom is disabled, skipping Prometheus DB reset")
        return

Sometimes, the test orchestration doesn't need to handle some
configuration flags, but only pass them to the toolbox layer. TOPSAIL
provides a helper toolbox command for that: ``from_config``.

Example:

::

    rhods:
      catalog:
        image: brew.registry.redhat.io/rh-osbs/iib
        tag: 804339
        channel: fast
        version: 2.13.0
        version_name: rc1
        opendatahub: false
        managed_rhoi: true

These configuration flags should be passed directly to the ``rhods
deploy_ods`` toolbox command

::

    def deploy_ods(self, catalog_image, tag, channel="", version="",
                   disable_dsc_config=False, opendatahub=False, managed_rhoai=True):
        """
        Deploy ODS operator from its custom catalog

        Args:
          catalog_image: Container image containing the RHODS bundle.
          tag: Catalog image tag to use to deploy RHODS.
          channel: The channel to use for the deployment. Let empty to use the default channel.
          ...
        """

So the way to launch the RHOAI deployement should be:

::

    run.run_toolbox("rhods", "deploy_ods"
                    catalog_image=config.project.get_config("rhods.catalog.image"),
                    tag=config.project.get_config("rhods.catalog.tag"),
                    channel=config.project.get_config("rhods.catalog.channel"),
                    ...)

Instead, the orchestration can use the ``command_args.yaml.j2`` file:

::

    rhods deploy_ods:
      catalog_image: {{ rhods.catalog.image }}
      tag: {{ rhods.catalog.tag }}
      channel: {{ rhods.catalog.channel }}
      ...

where the template will be generated from the configuration file. And
this command will trigger it:

::

    run.run_toolbox_from_config("rhods", "deploy_ods")


or this equivalent, from the command-line:

::

    source ./projects/fine_tuning/testing/configure.sh
    ./run_toolbox.py from_config rhods deploy_ods

Configuring the configuration with presets
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

TOPSAIL configuration can be updated through the presets. This allows
storing multiple different test flavors side by side, and deciding at
launch time which one to execute.

The presets, stored inside in the configuration in the ``ci_presets``
field, define how to update the main configuration blocks before
running the test.

Here is an example, which will test multiple dataset replication
factors:

::

  dgx_single_model_multi_dataset:
    extends: [dgx_single_model]
    tests.fine_tuning.matbenchmarking.enabled: true
    tests.fine_tuning.test_settings.gpu: 1
    tests.fine_tuning.test_settings.dataset_replication: [1, 2, 4, 8]

We see that three fields are "simply" updated. The ``extends`` keyword
means that first of all (because it is in the first position), we need
to apply the ``dgx_single_model`` preset, and only after modify the
three fields.

The presets are applied with a simple recursive algorithm (which will
dirtily crash if there is a loop in the presets ^.^). If multiple
presets are defined, and they touch the same values, only the last
change will be visible. Same for the ``extends`` keyword. It applied
at its position in the dictionary.

Last important point: the presets **cannot** create new fields. This
can be worked around by having placeholders in the main
configuration. Eg:

::

  tests:
    fine_tuning:
      test_settings:
          hyper_parameters:
            per_device_train_batch_size: null
            gradient_accumulation_steps: null

And everything is YAML. So the preset values can be YAML dictionaries
(or lists).

::

  tests.fine_tuning.test_settings.hyper_parameters: {r: 4, lora_alpha: 16}

This would work even if no placeholder has been set for ``r`` and
``lora_alpha``, because the ``hyper_parameters`` is being assigned
(and everything it contained before would be erased).


Calling the toolbox commands
============================

The "orchestration" layer orchestrates the toolbox commands. That is,
it calls them, in the right order, according to configuration flags,
and with the right parameters.

The Python code can call the toolbox directly, by passing all the
necessary arguments:

::

    has_dsc = run.run("oc get dsc -oname", capture_stdout=True).stdout
    run.run_toolbox(
        "rhods", "update_datasciencecluster",
        enable=["kueue", "codeflare", "trainingoperator"],
        name=None if has_dsc else "default-dsc",
    )

or from the configuration:

::

    run.run_toolbox_from_config("rhods", "deploy_ods")

But it can also have a "mix" of both, via the ``extra`` arguments of
the ``from_config`` call:


::

   extra = dict(source=source, storage_dir=storage_dir, name=source_name)
   run.run_toolbox_from_config("cluster", "download_to_pvc", extra=extra)

This way, ``cluster download_to_pvc`` will have parameters received
from the configuration, and extra settings (which take precedence),
prepared directly in Python.

The ``from_config`` command also accepts a prefix and/or a
suffix. Indeed, one command might be called with different parameters
in the same workflow.

A simple example is the ``cluster set_scale`` command, which is used,
in cloud environment, to control the number of nodes dedicated to a
given task.

::

    sutest/cluster set_scale:
      name: {{ clusters.sutest.compute.machineset.name }}
      instance_type: {{ clusters.sutest.compute.machineset.type }}
      scale: SET_AT_RUNTIME

    driver/cluster set_scale:
      instance_type: {{ clusters.driver.compute.machineset.type }}
      name: {{ clusters.driver.compute.machineset.name }}
      scale: SET_AT_RUNTIME

This will be called with the ``prefix`` parameter:

::

   run.run_toolbox_from_config("cluster", "set_scale", prefix="sutest", extra=dict(scale=...))
   run.run_toolbox_from_config("cluster", "set_scale", prefix="driver", extra=dict(scale=...))

and the same works for the suffix:

::

    prefix/command sub-command/suffix: ...


Creating dedicated directories
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The artifacts are a critical element for TOPSAIL post-mortem
processing and troubleshooting. But when the orchestration starts to
involve multiple commands, it gets complicated to understand what is
done at which step.

So TOPSAIL provides the ``env.NextArtifactDir`` context, which creates
a dedicated directory (with a ``nnn__`` prefix to enforce the correct
ordering).

Inside this directory, ``env.ARTIFACT_DIR`` will be correctly, so that
the code can write its artifact files in a dedicated directory.

::

   with env.NextArtifactDir("multi_model_test_sequentially"):

This is mostly used in the ``test`` part, to group the multiple
commands related to a test together.

Running toolbox commands in parallel
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When the orchestration preparation starts to involve multiple
commands, running all of them sequentially make take forever.

So TOPSAIL provides the ``run.Parallel`` context and the
``parallel.delayed`` function to allow running multiple commands in
parallel:

::

    with run.Parallel("prepare_scale") as parallel:
        parallel.delayed(prepare_kserve.prepare)
        parallel.delayed(scale_up_sutest)

        parallel.delayed(prepare_user_pods.prepare_user_pods, user_count)
        parallel.delayed(prepare_user_pods.cluster_scale_up, user_count)

This will create a dedicated directory, and at the end of the block it
will execute the 4 functions in dedicated threads.

Mind that the configuration **cannot** be updated inside a parallel
region (eg,
``config.project.set_config("tests.scale.model.consolidated", True)``).
