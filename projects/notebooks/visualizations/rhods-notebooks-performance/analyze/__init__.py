import projects.matrix_benchmarking.visualizations.helpers.analyze as helpers_analyze

COMPARISON_KEYS = ["rhoai_version", "image_tag"]

IGNORED_KEYS = ["ocp_version", "rhoai_version", "image"]


def _rewrite_settings(settings_dict):
    del settings_dict["image"]

    if settings_dict["ci_engine"] == "Middleware Jenkins":
        settings_dict["ci_engine"] = "PERFLAB_CI"

    return settings_dict


def prepare():
    return helpers_analyze.prepare_regression_data(COMPARISON_KEYS, IGNORED_KEYS, _rewrite_settings)
