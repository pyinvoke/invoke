#!/usr/bin/env python

# Support setuptools only, distutils has a divergent and more annoying API and
# few folks will lack setuptools.
from setuptools import setup, find_packages

# Version info -- read without importing
_locals = {}
with open("invoke/_version.py") as fp:
    exec(fp.read(), None, _locals)
version = _locals["__version__"]

exclude = []

# Frankenstein long_description
long_description = """
{}

For a high level introduction, including example code, please see `our main
project website <https://pyinvoke.org>`_; or for detailed API docs, see `the
versioned API website <https://docs.pyinvoke.org>`_.
""".format(
    open("README.rst").read()
)


setup(
    name="invoke",
    version=version,
    description="Pythonic task execution",
    license="BSD",
    long_description=long_description,
    author="Jeff Forcier",
    author_email="jeff@bitprophet.org",
    url="https://pyinvoke.org",
    project_urls={
        "Docs": "https://docs.pyinvoke.org",
        "Source": "https://github.com/pyinvoke/invoke",
        "Issues": "https://github.com/pyinvoke/invoke/issues",
        "Changelog": "https://www.pyinvoke.org/changelog.html",
        "CI": "https://app.circleci.com/pipelines/github/pyinvoke/invoke",
    },
    python_requires=">=3.6",
    packages=find_packages(exclude=exclude),
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
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Software Distribution",
        "Topic :: System :: Systems Administration",
    ],
)
