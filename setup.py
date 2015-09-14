# -*- Mode: Python -*-

from setuptools import setup, find_packages
from distutils.extension import Extension

from Cython.Build import cythonize

ext_modules = cythonize ([ Extension ('cys2n.cys2n', ['cys2n/cys2n.pyx'], libraries = ['s2n'])])

setup (
    name='cys2n',
    version='0.1',
    description='Cython wrapper for Amazon s2n',
    author='Sam Rushing',
    license="BSD",
    url="http://github.com/samrushing/cys2n",
    packages = find_packages(),
    package_data = {'cys2n': ['*.pxd']},
    ext_modules= ext_modules,
    download_url = 'https://pypi.python.org/pypi?name=cys2n',
)

