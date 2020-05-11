from setuptools import setup
from Cython.Build import cythonize

setup(
    name='petsi',
    version='0.1',
    packages=['petsi'],
    url='',
    license='MIT',
    author='vadaszd',
    author_email='',
    description='',
    ext_modules = cythonize("helloworld.pyx"),
)
