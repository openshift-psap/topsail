Creating a new visualization module
===================================

TOPSAIL post-processing/visualization rely on MatrixBenchmarking
modules.  The post-processing steps are configured within the
``matbench`` field of the configuration file:

::

    matbench:
      preset: null
      workload: projects.fine_tuning.visualizations.fine_tuning
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
          index: topsail-fine-tuning
          index_prefix: ""
          prom_index_suffix: -prom
        regression_analyses:
          enabled: false
          # if the regression analyses fail, mark the test as failed
          fail_test_on_regression: false

The visualization modules are split into several sub-modules, that are
described below.

The ``store`` module
--------------------

The ``store`` module is built as an extension of
``projects.matrix_benchmarking.visualizations.helpers.store``, which
defines the ``store`` architecture usually used in TOPSAIL.

::

    local_store = helpers_store.BaseStore(
        cache_filename=CACHE_FILENAME, important_files=IMPORTANT_FILES,

        artifact_dirnames=parsers.artifact_dirnames,
        artifact_paths=parsers.artifact_paths,

        parse_always=parsers.parse_always,
        parse_once=parsers.parse_once,

        # ---

        lts_payload_model=models_lts.Payload,
        generate_lts_payload=lts_parser.generate_lts_payload,

        # ---

        models_kpis=models_kpi.KPIs,
        get_kpi_labels=lts_parser.get_kpi_labels,
    )

The upper part defines the core of the ``store`` module. It is
mandatory.

The lower parts define the LTS payload and KPIs. This part if
optional, and only required to push KPIs to OpenSearch.

The store parsers
~~~~~~~~~~~~~~~~~

The goal of the ``store.parsers`` module is to turn TOPSAIL test
artifacts directories into a Python object, that can be plotted or
turned into LTS KPIs.

The parsers of the main workload components rely on the ``simple``
store.

::

   store_simple.register_custom_parse_results(local_store.parse_directory)

The ``simple`` store searches for a ``settings.yaml`` file and an
``exit_code`` file.

When these two files are found, the parsing of a test begins, and the
current directory is considered a test root directory.

The parsing is done this way:

::

   if exists(CACHE_FILE) and not MATBENCH_STORE_IGNORE_CACHE == true:
     results = reload(CACHE_FILE)
   else:
     results = parse_once()

   parse_always(results)
   results.lts = parse_lts(results)
   return results

This organization improves the flexibility of the parsers, wrt to what
takes time (should be in ``parse_once``) vs what depends on the
current execution environment (should be in ``parse_always``).

Mind that if you are working on the parsers, you should disable the
cache, or your modifications will not be taken into account.

::

   export MATBENCH_STORE_IGNORE_CACHE=true

You can re-enable it afterwards with:

::

   unset MATBENCH_STORE_IGNORE_CACHE

The results of the main parser is a ``types.SimpleNamespace``
object. By choice, it is weakly (on the fly) defined, so the
developers must take care to properly propagate any modification of
the structure. We tested having a Pydantic model, but that turned out
to be to cumbersome to maintain. Could be retested.

The important part of the parser is triggered by the execution of this
method:

::

    def parse_once(results, dirname):
        results.test_config = helpers_store_parsers.parse_test_config(dirname)
        results.test_uuid = helpers_store_parsers.parse_test_uuid(dirname)
        ...

This ``parse_once`` method is in charge of transforming a directory
(``dirname``) into a Python object (``results``). The parse heavily
relies on ``obj = types.SimpleNamespace()`` objects, which are
dictionaries which fields can be access as attributes. The inner
dictionary can be accessed with ``obj.__dict__`` for programmatic
traversal.

The ``parse_once`` method should delegate the parsing to submethods,
which typically looks like this (safety checks have been removed for
readability):


::

    def parse_once(results, dirname):
        ...
        results.finish_reason = _parse_finish_reason(dirname)
        ....

    @helpers_store_parsers.ignore_file_not_found
    def _parse_finish_reason(dirname):
        finish_reason = types.SimpleNamespace()
        finish_reason.exit_code = None

        with open(register_important_file(dirname, artifact_paths.FINE_TUNING_RUN_FINE_TUNING_DIR / "artifacts/pod.json")) as f:
            pod_def = json.load(f)

        finish_reason.exit_code = container_terminated_state["exitCode"]

        return finish_reason

Note that:

* for efficiency, JSON parsing should be preferred to YAML parsing,
  which is much slower.
* for grep-ability, the ``results.xxx`` field name should match the
  variable defined in the method (``xxx = types.SimpleNamespace()``)
* the ``ignore_file_not_found`` decorator will catch
  ``FileNotFoundError`` exceptions and return ``None`` instead. This
  makes the code resilient against not-generated artifacts. This
  happens "often" while performing investigations in TOPSAIL, because
  the test failed in an unexpected way. The visualization is expected
  to perform as best as possible when this happens (graceful
  degradation), so that the rest of the artifacts can be exploited to
  understand what happened and caused the failure.

The difference between these two methods:

::

    def parse_once(results, dirname): ...

    def parse_always(results, dirname, import_settings): ..

is that ``parse_once`` is called once, then the results is saved into
a cache file, and reloaded from there, the environment variable
``MATBENCH_STORE_IGNORE_CACHE=y`` is set.

Method ``parse_always`` is always called, even after reloading the
cache file. This can be used to parse information about the
environment in which the post-processing is executed.

::

    artifact_dirnames = types.SimpleNamespace()
    artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR = "*__cluster__capture_environment"
    artifact_dirnames.FINE_TUNING_RUN_FINE_TUNING_DIR = "*__fine_tuning__run_fine_tuning_job"
    artifact_dirnames.RHODS_CAPTURE_STATE = "*__rhods__capture_state"
    artifact_paths = types.SimpleNamespace() # will be dynamically populated

This block is used to lookup the directories where the files to be
parsed are stored (the prefix ``nnn__`` can change easily, so it
shouldn't be hardcoded).

During the initialization of the store module, the directories listed
by ``artifacts_dirnames`` are resolved and stored in the
``artifacts_paths`` namespace. They can be used in the parser with,
eg: ``artifact_paths.FINE_TUNING_RUN_FINE_TUNING_DIR /
"artifacts/pod.log"``.

If the directory blob does not resolve to a file, its value is ``None``.

::

    IMPORTANT_FILES = [
        ".uuid",
        "config.yaml",
        f"{artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR}/_ansible.log",
        f"{artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR}/nodes.json",
        f"{artifact_dirnames.CLUSTER_CAPTURE_ENV_DIR}/ocp_version.yml",
        f"{artifact_dirnames.FINE_TUNING_RUN_FINE_TUNING_DIR}/src/config_final.json",
        f"{artifact_dirnames.FINE_TUNING_RUN_FINE_TUNING_DIR}/artifacts/pod.log",
        f"{artifact_dirnames.FINE_TUNING_RUN_FINE_TUNING_DIR}/artifacts/pod.json",
        f"{artifact_dirnames.FINE_TUNING_RUN_FINE_TUNING_DIR}/_ansible.play.yaml",
        f"{artifact_dirnames.RHODS_CAPTURE_STATE}/rhods.createdAt",
        f"{artifact_dirnames.RHODS_CAPTURE_STATE}/rhods.version",
    ]


This block defines the files important for the parsing. They are
"important" and not "mandatory" as the parsing should be able to
proceed even if the files are missing.

The list of "important files" is used when downloading results for
re-processing. The download command can either lookup the cache file,
or download all the important files. A warning is issued during the
parsing if a file opened with ``register_important_file`` is not part
of the import files list.

The ``store`` and ``models`` LTS and KPI modules
------------------------------------------------

The Long-Term Storage (LTS) payload and the Key Performance Indicators
(KPIs) are TOPSAIL/MatrixBenchmarking features for Continuous
Performance Testing (CPT).

* The LTS payload is a "complex" object, with ``metadata``,
  ``results`` and ``kpis`` fields. The ``metadata``, ``results`` are
  defined with Pydantic models, which enforce their structure. This
  was the first attempt of TOPSAIL/MatrixBenchmarking to go towards
  long-term stability of the test results and metadata. This attempt
  has not been convincing, but it is still part of the pipeline for
  historical reasons. Any metadata or result can be stored in these
  two objects, provided that you correctly add the fields in the
  models.
* The KPIs is our current working solution for continuous performance
  testing. A KPI is a simple object, which consists in a value, a help
  text, a timestamp, a unit, and a set of labels. The KPIs follow the
  OpenMetrics idea.

::

   # HELP kserve_container_cpu_usage_max Max CPU usage of the Kserve container | container_cpu_usage_seconds_total
   # UNIT kserve_container_cpu_usage_max cores
   kserve_container_cpu_usage_max{instance_type="g5.2xlarge", accelerator_name="NVIDIA-A10G", ocp_version="4.16.0-rc.6", rhoai_version="2.13.0-rc1+2024-09-02", model_name="flan-t5-small", ...} 1.964734477279039

Currently, the KPIs are part of the LTS payload, and the labels are
duplicated for each of the KPIs. This designed will be reconsidered in
the near future.

Definition of KPI labels and values
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The KPIs are a set of performance indicators and labels.

The KPIs are defined by functions which extract the KPI value by
inspecting the LTS payload:

::

   @matbench_models.HigherBetter
   @matbench_models.KPIMetadata(help="Number of dataset tokens processed per seconds per GPU", unit="tokens/s")
   def dataset_tokens_per_second_per_gpu(lts_payload):
      return lts_payload.results.dataset_tokens_per_second_per_gpu

the name of the function is the name of the KPI, and the annotation
define the metadata and some formatting properties:

::

   # mandatory
   @matbench_models.KPIMetadata(help="Number of train tokens processed per GPU per seconds", unit="tokens/s")

   # one of these two is mandatory
   @matbench_models.LowerBetter
   # or
   @matbench_models.HigherBetter

   # ignore this KPI in the regression analyse
   @matbench_models.IgnoredForRegression

   # simple value formatter
   @matbench_models.Format("{:.2f}")

   # formatter with a divisor (and a new unit)
   @matbench_models.FormatDivisor(1024, unit="GB", format="{:.2f}")

The KPI labels are defined via a Pydantic model:

::

   KPI_SETTINGS_VERSION = "1.0"
   class Settings(matbench_models.ExclusiveModel):
      kpi_settings_version: str
      ocp_version: matbench_models.SemVer
      rhoai_version: matbench_models.SemVer
      instance_type: str

      accelerator_type: str
      accelerator_count: int

      model_name: str
      tuning_method: str
      per_device_train_batch_size: int
      batch_size: int
      max_seq_length: int
      container_image: str

      replicas: int
      accelerators_per_replica: int

      lora_rank: Optional[int]
      lora_dropout: Optional[float]
      lora_alpha: Optional[int]
      lora_modules: Optional[str]

      ci_engine: str
      run_id: str
      test_path: str
      urls: Optional[dict[str, str]]

So eventually, the KPIs are the combination of the generic part
(``matbench_models.KPI``) and project specific labels (``Settings``):

::

   class KPI(matbench_models.KPI, Settings): pass
   KPIs = matbench_models.getKPIsModel("KPIs", __name__, kpi.KPIs, KPI)


Definition of the LTS payload
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The LTS payload was the original idea of the document to save for
continuous performance testing. KPIs have replaced them in this
endeavor, but in the current state of the project, the LTS payload
includes the KPIs. The LTS payload is the object actually sent to the
OpenSearch database.

The LTS Payload is composed of three objects:

- the metadata (replaced by the KPI labels)
- the results (replace by the KPI values)
- the KPIs

::

  LTS_SCHEMA_VERSION = "1.0"
  class Metadata(matbench_models.Metadata):
      lts_schema_version: str
      settings: Settings

      presets: List[str]
      config: str
      ocp_version: matbench_models.SemVer

   class Results(matbench_models.ExclusiveModel):
      train_tokens_per_second: float
      dataset_tokens_per_second: float
      gpu_hours_per_million_tokens: float
      dataset_tokens_per_second_per_gpu: float
      train_tokens_per_gpu_per_second: float
      train_samples_per_second: float
      train_runtime: float
      train_steps_per_second: float
      avg_tokens_per_sample: float

   class Payload(matbench_models.ExclusiveModel):
      metadata: Metadata
      results: Results
      kpis: KPIs

Generation of the LTS payload
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The generation of the LTS payload is done after the parsing of main
artifacts.

::

  def generate_lts_payload(results, import_settings):
      lts_payload = types.SimpleNamespace()

      lts_payload.metadata = generate_lts_metadata(results, import_settings)
      lts_payload.results = generate_lts_results(results)
      # lts_payload.kpis is generated in the helper store

      return lts_payload

On purpose, the parser does *not* use the Pydantic model when creating
the LTS payload.  The reason for that is that the parser is strict. If
a field is missing, the object will not be created and an exception
will be raised.  When TOPSAIL is used for running performance
investigations (in particular scale tests), we do not what this,
because the test might terminate with some artifacts missing. Hence,
the parsing will be incomplete, and we do *not* want that to abort the
visualization process.

However, when running in continuous performance testing mode, we do
want to guarantee that everything is correctly populated.

So TOPSAIL will run the parsing twice. First, without checking the LTS
conformity:

::

   matbench parse
        --output-matrix='.../internal_matrix.json' \
	--pretty='True' \
	--results-dirname='...' \
	--workload='projects.kserve.visualizations.kserve-llm'

Then, when LTS generation is enabled, with the LTS checkup:

::

   matbench parse \
	--output-lts='.../lts_payload.json' \
	--pretty='True' \
	--results-dirname='...' \
	--workload='projects.kserve.visualizations.kserve-llm'

This step (which reload from the cache file) will be recorded as a
failure if the parsing is incomplete.


Generation of the KPI values
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The KPI values are generated in two steps:

First the ``KPIs`` dictionary is populated when the ``KPIMetadata``
decorator is applied to a function (``function name --> dict with the
function, metadata, format, etc``)

::

   KPIs = {} # populated by the @matbench_models.KPIMetadata decorator
   # ...
   @matbench_models.KPIMetadata(help="Number of train tokens processed per seconds", unit="tokens/s")
   def train_tokens_per_second(lts_payload):
     return lts_payload.results.train_tokens_per_second

Second, when the LTS payload is generated via the ``helpers_store``

::

   import projects.matrix_benchmarking.visualizations.helpers.store as helpers_store

the LTS payload is passed to the KPI function, and the full KPI is
generated.

The ``plotting`` visualization module
-------------------------------------

The ``plotting`` module contains two kind of classes: the "actual"
plotting classes, which generate Plotly plots, and the report classes,
which generates HTML pages, based on Plotly's Dash framework.

The ``plotting`` plot classes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``plotting`` plot classes generate Plotly plots. They receive a
set of parameters about what should be plotted:

::

   def do_plot(self, ordered_vars, settings, setting_lists, variables, cfg):
       ...

and they return a Plotly figure, and optionally some text to write
below the plot:

::

   return fig, msg

The parameters are mostly useful when multiple experiments have been
captured:

- ``setting_lists`` and ``settings`` should not be touched. They
  should be passed to ``common.Matrix.all_records``, which will return
  a filtered list of all the entry to include in the plot.

::

   for entry in common.Matrix.all_records(settings, setting_lists):
       # extract plot data from entry
       pass

Some plotting classes may be written to display only one experiment
results. A fail-safe exit can be written this way:

::

   if common.Matrix.count_records(settings, setting_lists) != 1:
       return {}, "ERROR: only one experiment must be selected"

- the ``variables`` dictionary tells which settings have multiple
  values. Eg, we may have 6 experiments, all with
  ``model_name=llama3``, but with ``virtual_users=[4, 16, 32]`` and
  ``deployment_type=[raw, knative]``. In this case, the
  ``virtual_users`` and ``deployment_type`` will be listed in the
  ``variables``. This is useful to give a name to each entry. Eg,
  here, ``entry.get_name(variables)``  may return ``virtual_users=16,
  deployment_type=raw``.

- the ``ordered_vars`` list tells the preferred ordering for
  processing the experiments. With the example above and
  ``ordered_vars=[virtual_users, deployment_type]``, we may want to
  use the virtual_user setting as legend. With
  ``ordered_vars=[deployment_type, virtual_users]``, we may want to
  use the ``deployment_type`` instead. This gives flexibility in the
  way the plots are rendered. This order can be set in the GUI, or via
  the reporting calls.

Note that using these parameters is optional. They have no sense when
only one experiment should be plotted, and ``ordered_vars`` is useful
only when using the GUI, or when generating reports. They help the
generic processing of the results.

- the ``cfg`` dictionary provides some dynamic configuration flags to
  perform the visualization. They can be passed either via the GUI, or
  by the report classes (eg, to highlight a particular aspect of the
  plot).


Guideline for writing the plotting classes
""""""""""""""""""""""""""""""""""""""""""

Writing a plotting class is often messy and dirty, with a lot of
``if`` this ``else`` that. With Plotly's initial framework
``plotly.graph_objs``, it was easy and tempting to mix the data
preparation (traversing the data structures) with the data
visualization (adding elements like lines to the plot), and do both
parts in the same loops.

Plotly express (``plotly.express``) introduced a new way to generate
the plots, based on Pandas DataFrames:

::

   df = pd.DataFrame(generateThroughputData(entries, variables, ordered_vars, cfg__model_name))
   fig = px.line(df, hover_data=df.columns,
                 x="throughput", y="tpot_mean", color="model_testname", text="test_name",)

This pattern, where the first phase shapes the data to plot into
DataFrame, and the second phase turns the DataFrame into a figure, is
the preferred way to organize the code of the plotting classes.

The ``plotting`` reports
^^^^^^^^^^^^^^^^^^^^^^^^


The report classes are similar to the plotting classes, except that
they generate ... reports, instead of plots (!).

A report is an HTML document, based on the Dash framework HTML tags
(that is, Python objects):

::

   args = ordered_vars, settings, setting_lists, variables, cfg

   header += [html.H1("Latency per token during the load test")]

   header += Plot_and_Text(f"Latency details", args)
   header += html.Br()
   header += html.Br()

   header += Plot_and_Text(f"Latency distribution", args)

   header += html.Br()
   header += html.Br()

The configuration dictionary, mentioned above, can be used to generate
different flavors of the plot:

::

   header += Plot_and_Text(f"Latency distribution", set_config(dict(box_plot=False, show_text=False), args))

   for entry in common.Matrix.all_records(settings, setting_lists):
       header += [html.H2(entry.get_name(reversed(sorted(set(list(variables.keys()) + ['model_name'])))))]
       header += Plot_and_Text(f"Latency details", set_config(dict(entry=entry), args))

Defining the plots and reports to generate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When TOPSAIL has successfully run the parsing step, it calls the
``visualization`` component with a predefined list of reports
(preferred) and plots (not recommended) to generate. This is stored in
``data/plots.yaml``:

::

   visualize:
   - id: llm_test
     generate:
     - "report: Error report"
     - "report: Latency per token"
     - "report: Throughput"

The ``analyze`` regression analyze module
-----------------------------------------

The last part of TOPSAIL/MatrixBenchmarking post-processing is the
automated regression analyses. The workflow required to enable performance
analyses will be described in the orchestration section. What is
required in the workload module only consists of a few keys to define.


::

   # the setting (kpi labels) keys against which the historical regression should be performed
   COMPARISON_KEYS = ["rhoai_version"]

The setting keys listed in ``COMPARISON_KEYS`` will be used to
distinguish which entries to considered as "history" for a given test,
from everything else. In this example, we see that we compare against
historical OpenShift AI versions.

::

   COMPARISON_KEYS = ["rhoai_version", "image_tag"]

Here, we compare against the historical RHOAI version and image tag.

::

   # the setting (kpi labels) keys that should be ignored when searching for historical results
   IGNORED_KEYS = ["runtime_image", "ocp_version"]

Then we define the settings to ignore when searching for historical
records. Here, we ignore the runtime image name, and the OpenShift
version.

::

   # the setting (kpi labels) keys *prefered* for sorting the entries in the regression report
   SORTING_KEYS = ["model_name", "virtual_users"]

Finally, for readability purpose, we define how the entries should be
sorted, so that the tables have a consistent ordering.

::

   IGNORED_ENTRIES = {
       "virtual_users": [4, 8, 32, 128]
   }

Last, we can define some settings to ignore while traversing the
entries that have been tested.
