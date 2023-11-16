#!/usr/bin/env python

"""
Copyright TOPSAIL contributors.

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at:

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
"""

import os
from sys import version_info
import pathlib
import itertools
from setuptools import find_packages, setup
from topsail.__info__ import version

if version_info < (3, 9):
    raise RuntimeError(
        'Python 3.9 or greater is required'
    )

_NAME = 'topsail'
_DESCRIPTION = 'topsail CLI'
_REVISION = str(version)

topsail_revision = os.environ.get('TOPSAIL_REVISION', "")
if (topsail_revision != ""):
    _REVISION = _REVISION + "." + topsail_revision

if os.path.isfile('.README.md'):
    with open('.README.md') as f:
        long_description = f.read()
else:
    long_description = _DESCRIPTION

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name=_NAME,
    version=_REVISION,
    description=_DESCRIPTION,
    long_description_content_type='text/markdown',
    long_description=long_description,
    url='https://github.com/openshift-psap/topsail',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development :: Testing',
    ],
    author='TOPSAIL',
    include_package_data=True,
    install_requires=requirements,
    py_modules=['run_toolbox'],
    entry_points={
        'console_scripts': [
            # TODO:FIXME: The CLI entrypoint
            # should be part of the topsail package,
            # for backwards compatibility this is
            # not possible unless run_toolbox.py is
            # inside the topsail package folder
            '{0} = {0}.__main__:main'.format(_NAME),
        ]
    }
)
