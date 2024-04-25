import sys, os
import logging
import traceback
import copy
import pathlib
import yaml
import uuid

from projects.core.library import env, config, run, visualize, matbenchmark
import prepare_finetuning

TESTING_THIS_DIR = pathlib.Path(__file__).absolute().parent
TOPSAIL_DIR = pathlib.Path(config.__file__).parents[3]
RUN_DIR = pathlib.Path(os.getcwd()) # for run_one_matbench
os.chdir(TOPSAIL_DIR)

def test():
    print("Nothing")
