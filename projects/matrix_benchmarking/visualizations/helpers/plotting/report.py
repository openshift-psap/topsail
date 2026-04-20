import copy
import logging

from dash import dcc
from dash import html

import matrix_benchmarking.plotting.table_stats as table_stats


def set_config(additional_cfg, args):
    cfg = copy.deepcopy(args[-1])
    cfg.d.update(additional_cfg)
    return list(args[:-1]) + [cfg]


def set_settings(new_settings, args):
    """
    Set specific settings and remove them from variables to fix the plot dimensions

    Args:
        new_settings: Dict of settings to apply (e.g., {"model": "gpt-oss-120b"})
        args: Original plot arguments

    Returns:
        Updated args with settings applied and variables modified
    """
    # Make deep copies to avoid modifying the original
    args_copy = copy.deepcopy(args)
    ordered_vars, settings, setting_lists, variables, cfg = args_copy

    # Update settings with new values
    settings.update(new_settings)

    # Remove the keys from variables so they're no longer treated as varying dimensions
    for key in new_settings.keys():
        if key in variables:
            del variables[key]

    # Update setting_lists to remove dimensions that are now fixed
    # setting_lists is a list of lists like:
    # [[('model', 'gpt-oss-120b'), ('model', 'llama3.3-70b')], [('load_shape', 'Heterogeneous'), ('load_shape', 'Multiturn')]]
    updated_setting_lists = []
    for setting_list in setting_lists:
        # Check if this setting_list corresponds to a dimension we're fixing
        if setting_list and setting_list[0][0] not in new_settings:
            # Keep this dimension since we're not fixing it
            updated_setting_lists.append(setting_list)

    # Replace the setting_lists with the filtered version
    setting_lists[:] = updated_setting_lists

    return ordered_vars, settings, setting_lists, variables, cfg


def set_entry(entry, _args):
    args = copy.deepcopy(_args)
    ordered_vars, settings, setting_lists, variables, cfg = args

    settings.update(entry.settings.__dict__)
    setting_lists[:] = []
    variables.clear()
    return args


def Plot(name, args, msg_p=None):
    try:
        stats = table_stats.TableStats.stats_by_name[name]
    except KeyError:
        logging.error(f"Report: Stats '{name}' does not exist. Skipping it.")
        stats = None

    fig, msg = stats.do_plot(*args) if stats else (None, f"Stats '{name}' does not exit :/")

    if msg_p is not None: msg_p.append(msg)

    return dcc.Graph(figure=fig)


def Plot_and_Text(name, args):
    msg_p = []

    data = [Plot(name, args, msg_p)]

    if msg_p[0]:
        data.append(
            html.Div(
                msg_p[0],
                style={"border-radius": "5px",
                       "padding": "0.5em",
                       "background-color": "lightgray",
                       }))

    return data
