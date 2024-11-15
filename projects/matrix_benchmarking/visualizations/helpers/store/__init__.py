import types
import logging
import os
import pathlib
import pickle
import fnmatch
import json
import functools

import jsonpath_ng

from matrix_benchmarking.parse import json_dumper
import matrix_benchmarking.store as store
import matrix_benchmarking.common as common

class BaseStore():
    def __init__(self, *,
                 cache_filename, important_files,
                 artifact_dirnames, artifact_paths,
                 extra_mandatory_files=[],
                 parse_always, parse_once,
                 generate_lts_payload=None, lts_payload_model=None,
                 models_kpis=None, get_kpi_labels=None,
                 ):

        self.cache_filename = cache_filename
        self.important_files = important_files
        self.extra_mandatory_files = extra_mandatory_files

        self.artifact_dirnames = artifact_dirnames
        self.artifact_paths = artifact_paths

        self.parse_always = parse_always
        self.parse_once = parse_once

        self.lts_payload_model = lts_payload_model
        if lts_payload_model:
            self.generate_lts_payload = generate_lts_payload
            store.register_lts_schema(lts_payload_model)
            self.models_kpis = models_kpis
            self.get_kpi_labels = get_kpi_labels

    def is_mandatory_file(self, filename):
        return (
            filename.name in ("settings", "exit_code", "config.yaml", "skip")
            or filename.name in self.extra_mandatory_files
            or filename.name.startswith("settings.")
        )

    def is_important_file(self, filename):
        if str(filename) in self.important_files:
            return True

        for important_file in self.important_files:
            if "*" not in important_file: continue

            if fnmatch.filter([str(filename)], important_file):
                return True

        return False

    def is_cache_file(self, filename):
        return filename.name == self.cache_filename

    def register_important_file(self, base_dirname, filename):
        to_return = base_dirname / filename
        if self.is_important_file(filename):
            return to_return

        filename_resolved = (base_dirname / filename).resolve().relative_to(base_dirname.resolve())
        if self.is_important_file(filename_resolved):
            # filename is composed of ..
            # accept it
            return to_return

        logging.warning(f"File '{filename}' not part of the important file list :/")
        if pathlib.Path(filename).is_absolute():
            logging.warning(f"File '{filename}' is an absolute path. Should be relative to {base_dirname}.")

        return to_return

    def resolve_artifact_dirnames(self, dirname):
        artifact_paths = types.SimpleNamespace()
        for artifact_dirname, unresolved_dirname in self.artifact_dirnames.__dict__.items():
            direct_resolution = dirname / unresolved_dirname
            if direct_resolution.exists():
                artifact_paths.__dict__[artifact_dirname] = pathlib.Path(unresolved_dirname)
                continue

            resolutions = list(dirname.glob(unresolved_dirname))
            resolved_dir = None

            if direct_resolution.exists():
                # all good
                resolved_dir = direct_resolution
            elif not resolutions:
                logging.warning(f"Cannot resolve {artifact_dirname} glob '{unresolved_dirname}' in '{dirname}'")
            else:
                if len(resolutions) > 1:
                    logging.debug(f"Found multiple resolutions for {artifact_dirname} glob '{unresolved_dirname}' in '{dirname}': {resolutions}. Taking the last one")
                    resolved_dir = [r.relative_to(dirname) for r in sorted(resolutions)][-1]
                else:
                    resolved_dir = resolutions[0].relative_to(dirname)

            artifact_paths.__dict__[artifact_dirname] = resolved_dir

        self.artifact_paths.__dict__.update(artifact_paths.__dict__)

    def load_cache(self, dirname):
        try:
            with open(dirname / self.cache_filename, "rb") as f:
                results = pickle.load(f)
        except FileNotFoundError:
            raise # will be catch at higher levels
        except Exception as e:
            logging.error("Could not reload the cache file: {e}")
            raise e

        self._prepare_after_pickle(results)
        self.prepare_after_pickle(results)

        return results


    def parse_directory(self, fn_add_to_matrix, dirname, import_settings, exit_code):
        ignore_cache = os.environ.get("MATBENCH_STORE_IGNORE_CACHE", False) in ("yes", "y", "true", "True")
        if not ignore_cache:
            try:
                results = self.load_cache(dirname)
            except FileNotFoundError:
                results = None # Cache file doesn't exit, ignore and parse the artifacts
        else:
            logging.info("MATBENCH_STORE_IGNORE_CACHE is set, not processing the cache file.")
            results = None

        if results:
            # reloaded from cache
            self.parse_always(results, dirname, import_settings)
            self.parse_lts(results, import_settings, exit_code)

            fn_add_to_matrix(results)

            return

        self.resolve_artifact_dirnames(dirname)

        results = types.SimpleNamespace()

        self.parse_once(results, dirname)
        self.parse_always(results, dirname, import_settings)
        self.parse_lts(results, import_settings, exit_code)

        fn_add_to_matrix(results)

        with open(dirname / self.cache_filename, "wb") as f:

            self.prepare_for_pickle(results)
            self._prepare_for_pickle(results)

            pickle.dump(results, f)

            self._prepare_after_pickle(results)
            self.prepare_after_pickle(results)

        print("parsing done :)")

    def parse_lts(self, results, import_settings, exit_code):
        if not self.lts_payload_model:
            return

        results.lts = lts_payload = self.generate_lts_payload(results, import_settings)
        if self.models_kpis:
            lts_payload.kpis = self.generate_lts_kpis(lts_payload)

        lts_payload.metadata.exit_code = exit_code

        validate_lts_payload(self.lts_payload_model, lts_payload, import_settings, reraise=False)


    def generate_lts_kpis(self, lts_payload):
        kpis = {}
        for name, properties in self.models_kpis.items():
            kpi = {} | properties | self.get_kpi_labels(lts_payload)

            kpi_func = kpi.pop("__func__")
            try:
                kpi["value"] = kpi_func(lts_payload)
            except Exception as e:
                logging.error(f"Failed to generate KPI {name}: {e}")
                kpi["value"] = None

            kpis[name] = types.SimpleNamespace(**kpi)

        return kpis

    def _prepare_for_pickle(self, results):
        pass

    def _prepare_after_pickle(self, results):
        pass

    def prepare_for_pickle(self, results):
        pass

    def prepare_after_pickle(self, results):
        pass

    def parse_data():
        # delegate the parsing to the simple_store
        store.register_custom_rewrite_settings(_rewrite_settings)
        store_simple.register_custom_parse_results(_parse_directory)

        from . import lts
        store_simple.register_custom_build_lts_payloads(lts.build_lts_payloads)

        return store_simple.parse_data()


    def build_lts_payloads(self):
        if not self.lts_payload_model:
            raise ValueError("Cannot build the LTS payload: no `lts_payload_model` defined in this workload.")

        for entry in common.Matrix.processed_map.values():
            results = entry.results
            lts_payload = results.lts

            validate_lts_payload(self.lts_payload_model, lts_payload, entry.import_settings, reraise=True)

            yield lts_payload, lts_payload.metadata.start, lts_payload.metadata.end


class _yaml_file_get():
    def __init__(self, filename, yaml_file):
        self.yaml_file = yaml_file

    def get(self, key, missing=...):
        jsonpath_expression = jsonpath_ng.parse(f'$.{key}')

        match = jsonpath_expression.find(self.yaml_file)
        if not match:
            if missing != ...:
                return missing

            raise KeyError(f"Key '{key}' not found in {self.filename} ...")

        return match[0].value

def get_yaml_get_key(filename, yaml_file):

    return _yaml_file_get(filename, yaml_file).get


def validate_lts_payload(lts_payload_model, payload, import_settings, reraise=False):
    try:
        json_lts = json.dumps(payload, indent=4, default=functools.partial(json_dumper, strict=False))
    except ValueError as e:
        logging.error(f"Couldn't dump the lts_payload into JSON :/ {e}")

        if reraise:
            raise

        return False

    parsed_lts = json.loads(json_lts)
    try:
        lts_payload_model.parse_obj(parsed_lts)
        return True

    except Exception as e:
        log_fct = logging.error if reraise else logging.warning
        log_fct(f"lts-error: Failed to validate the generated LTS payload against the model")
        log_fct(f"lts-error: entry settings: {import_settings}")

        if reraise:
            raise

        log_fct(f"lts-error: validation issue(s): {e}")

        return False
