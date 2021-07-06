
# Copyright (c) 2021 David Steele <dsteele@gmail.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later
# License-Filename: LICENSE

import os
import shutil
from distutils.command.clean import clean

from setuptools import setup


setup(
    name="comitup-watch",
    packages=["comitup_watch"],
    version='0.1',
    description="Monitor local Comitup-enabled devices",
    classifiers=[
        'Development Status :: 5 - Pre-Alpha',
        'Environment :: Console :: Curses',
        'Framework :: Asyncio',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved ' +
        ':: GNU General Public License v2 or later (GPLv2+)',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Topic :: System :: Networking',
        'Typing :: Typed',
    ],
    entry_points={
        'console_scripts': [],
    },
    options={
        'build_scripts': {
            'executable': '/usr/bin/python3',
        },
    },
    data_files=[],
    install_requires=["dbussy", "tabulate", "zeroconf"],
    setup_requires=["pytest-runner"],
    tests_require=['pytest'],
    author="David Steele",
    author_email="steele@debian.org",
    url='https://davesteele.github.io/comitup-watch/',
    )
