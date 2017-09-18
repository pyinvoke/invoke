#!/usr/bin/env python

# Support setuptools only, distutils has a divergent and more annoying API and
# few folks will lack setuptools.
from setuptools import setup, find_packages
import re
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
# (Have to take an axe to the README to remove all the doctest stuff, which
# PyPI doesn't have enabled and barfs on...sob.)
text = open('README.rst').read()
text = re.sub(r'testsetup:: .+', '::', text)
text = re.sub(r'testcleanup:: .+', '::', text)
text = re.sub(r'doctest:: .+', 'code-block::', text)
long_description = """
To find out what's new in this version of Invoke, please see `the changelog
<http://pyinvoke.org/changelog.html#{0}>`_.

{1}
""".format(version, text)


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
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
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
