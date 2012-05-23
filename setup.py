#!/usr/bin/env python

import sys

# Support setuptools or distutils
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# Import ourselves for version info
import invoke

# Frankenstein long_description: version-specific changelog note + README
v = invoke.__version__
long_description = """
To find out what's new in this version of Invoke, please see `the changelog
<http://docs.pyinvoke.org/en/%s/changelog.html>`_.

%s
""" % (v, open('README.rst').read())

requirements = ['lexicon']
if sys.version_info[:2] == (2, 6):
    requirements.append("argparse>=1.2.1")

setup(
    name='invoke',
    version=v,
    description='Pythonic task execution',
    license='BSD',

    long_description=long_description,
    author='Jeff Forcier',
    author_email='jeff@bitprophet.org',
    url='http://pyinvoke.org',

    install_requires=requirements,
    packages=["invoke"],
    entry_points={
        'console_scripts': [
            'invoke = invoke.cli:main',
        ]
    },

    classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: BSD License',
          'Operating System :: MacOS :: MacOS X',
          'Operating System :: Unix',
          'Operating System :: POSIX',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Topic :: Software Development',
          'Topic :: Software Development :: Build Tools',
          'Topic :: Software Development :: Libraries',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: System :: Software Distribution',
          'Topic :: System :: Systems Administration',
    ],
)
