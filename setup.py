# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

version = '0.2.0'
readme = open('README.rst').read()

setup(name='fluidity-sm',
      version=version,
      description='Fluidity: state machine implementation for Python objects',
      long_description=readme,
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2.4',
          'Programming Language :: Python :: 2.5',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.1',
          'Programming Language :: Python :: 3.2',
          'Topic :: Software Development :: Libraries',
      ],
      keywords='state machine python dsl',
      author='Rodrigo Manhães',
      author_email='rmanhaes@gmail.com',
      url='https://github.com/nsi-iff/fluidity',
      license='MIT License',
      packages=find_packages()
      )

