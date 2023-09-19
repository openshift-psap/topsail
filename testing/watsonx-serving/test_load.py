#!/usr/bin/env python

import sys, os
import pathlib
import subprocess
import logging
import datetime
import time
import functools

from common import env, config, run, visualize

def test():
    run.run("echo hello world")
