#!/usr/bin/env python

# Support setuptools only, distutils has a divergent and more annoying API and
# few folks will lack setuptools.
from setuptools import setup, find_packages
import sys

# Version info -- read without importing
_locals = {}
with open('invoke/_version.py') as fp:
    exec(fp.read(), None, _locals)
version = _locals['__version__']

# PyYAML ships a split Python 2/3 codebase. Unfortunately, some pip versions
# attempt to interpret both halves of PyYAML, yielding SyntaxErrors. Thus, we
# exclude whichever appears inappropriate for the installing interpreter.
exclude = ['*.yaml3' if sys.version_info[0] == 2 else '*.yaml2']

# Frankenstein long_description: version-specific changelog note + README
long_description = """
To find out what's new in this version of Invoke, please see `the changelog
<http://pyinvoke.org/changelog.html#%s>`_.

%s
""" % (version, open('README.rst').read())

setup(
    name='invoke',
    version=version,
    description='Pythonic task execution',
    license='BSD',

    long_description=long_description,
    author='Jeff Forcier',
    author_email='jeff@bitprophet.org',
    url='http://docs.pyinvoke.org',

    packages=find_packages(exclude=exclude),
    entry_points={
        'console_scripts': [
            'invoke = invoke.main:program.run',
            'inv = invoke.main:program.run',
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
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Software Distribution',
        'Topic :: System :: Systems Administration',
    ],
)
