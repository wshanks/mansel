#!/usr/bin/env python
import setuptools

with open("../README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="mansel-lib",
    version="0.1.0",
    author="https://github.com/willsALMANJ",
    author_email="wsha.code@gmail.com",
    description="Library for manual file selection",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/willsALMANJ/mansel",
    packages=[],
    py_modules=['mansel'],
    install_requires=[],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Environment :: X11 Applications :: Qt",
    ]
)
