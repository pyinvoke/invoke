#!/usr/bin/env python

# Support setuptools or distutils
try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

# Version info -- read without importing
_locals = {}
with open('invoke/_version.py') as fp:
    exec(fp.read(), None, _locals)
version = _locals['__version__']

# Frankenstein long_description: version-specific changelog note + README
long_description = """
To find out what's new in this version of Invoke, please see `the changelog
<http://docs.pyinvoke.org/en/%s/changelog.html>`_.

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

    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'invoke = invoke.cli:main',
            'inv = invoke.cli:main',
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
