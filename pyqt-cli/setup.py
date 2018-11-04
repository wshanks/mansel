#!/usr/bin/env python

# This file is part of mansel-pyqt.
#
# mansel-pyqt is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Foobar is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Foobar.  If not, see <https://www.gnu.org/licenses/>.

import setuptools

with open("../README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="mansel-pyqt",
    version="0.1.0",
    author="https://github.com/willsALMANJ",
    author_email="wsha.code@gmail.com",
    description="Tool for manual file selection",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/willsALMANJ/mansel-pyqt",
    entry_points={
        'console_scripts': ['mansel=mansel:main']},
    packages=[],
    py_modules=[],
    install_requires=['PyQt5', 'mansel-lib'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Environment :: X11 Applications :: Qt",
        "Topic :: Utilities",
    ]
)
