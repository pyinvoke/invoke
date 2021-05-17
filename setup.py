#!/usr/bin/env python

# Support setuptools only, distutils has a divergent and more annoying API and
# few folks will lack setuptools.
from setuptools import setup, find_packages
import sys

# Version info -- read without importing
_locals = {}
with open("invoke/_version.py") as fp:
    exec(fp.read(), None, _locals)
version = _locals["__version__"]

# PyYAML ships a Python 2 codebase. We exclude the vendored python2 version on
# python3 and depend on the PyYaml package for python3.
exclude = ["*.yaml2"] if sys.version_info[0] == 2 else []
install_requires = ["PyYAML"] if sys.version_info[0] == 3 else []

# Frankenstein long_description: version-specific changelog note + README
text = open("README.rst").read()
long_description = """
To find out what's new in this version of Invoke, please see `the changelog
<http://pyinvoke.org/changelog.html#{}>`_.

{}
""".format(
    version, text
)


setup(
    name="invoke",
    version=version,
    description="Pythonic task execution",
    license="BSD",
    long_description=long_description,
    author="Jeff Forcier",
    author_email="jeff@bitprophet.org",
    url="http://docs.pyinvoke.org",
    packages=find_packages(exclude=exclude),
    install_requires=install_requires,
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "invoke = invoke.main:program.run",
            "inv = invoke.main:program.run",
        ]
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: BSD License",
        "Operating System :: POSIX",
        "Operating System :: Unix",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Software Development",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Software Distribution",
        "Topic :: System :: Systems Administration",
    ],
)
