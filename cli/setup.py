#!/usr/bin/env python
import setuptools

with open("../README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="mansel",
    version="0.1.0",
    author="https://github.com/willsALMANJ",
    author_email="wsha.code@gmail.com",
    description="Tool for manual file selection",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/willsALMANJ/mansel",
    entry_points={
        'console_scripts': ['mansel=mansel:main']},
    packages=[],
    py_modules=[],
    install_requires=['PySide2', 'mansel-lib'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Environment :: X11 Applications :: Qt",
        "Topic :: Utilities",
    ]
)
