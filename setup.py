#!/usr/bin/env python

'Setup file and install script for ISA-Report tools.'

from setuptools import setup

setup(
    name = "isareport",
    version = "0.0.1",
    author = "Angel Pizarro",
    author_email = "angel@upenn.edu",
    description = "Turns ISA-TAB format into a pretty HTML5 report.",
    license = "MIT",
    url = "https://github.com/itmat/isareport",
    packages = ['isareport'],
    scripts = ['bin/isareport'],
    install_requires = ['mako','pyhaml','pygraphviz','slug','oset']
)

