
# Import setuptools before Cython, otherwise, both might disagree about the class to use
# See https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html

from setuptools import setup, find_packages, Extension
import os
import sys

package_name = "petsi"

with open("README.md", "r") as fh:
    long_description = fh.read()

cythonized_modules = ["Structure", "util", "fire_control", "meters", ]


def modules_with_suffix(modules, suffix):
    return [module_name + suffix for module_name in modules]


def modules_with_prefix_suffix(modules, prefix, suffix):
    return [os.path.join(prefix, module_name + suffix) for module_name in modules]


package_data = (
    modules_with_suffix(cythonized_modules, ".c") +
    modules_with_suffix(cythonized_modules, ".pxd") +
    # modules_with_suffix(cythonized_modules, ".html") +
    modules_with_suffix(cythonized_modules, ".pyi")
)

extension_args = dict()

# We only cythonize in development mode, i.e. when
#
#   setup.py develop
#
# is run. Otherwise we compile the shipped *.c files
if 'develop' in sys.argv and "--uninstall" not in sys.argv:
    from Cython.Build import cythonize

    extension_args.update(
        # Command line for the manual cythonization of individual modules use (on the example of meters.py):
        #
        #    cythonize --3str -a -f -i petsi/meters.py
        #
        ext_modules=cythonize([os.path.join(package_name, module_name + ".py")
                               for module_name in cythonized_modules
                               ],
                              force=True, annotate=True, language_level="3str"),
    )
else:
    extension_args.update(
        ext_package=package_name,
        ext_modules=[Extension(module_name, [os.path.join(package_name, module_name + ".c")])
                     for module_name in cythonized_modules
                     ],
    )

setup(
    name='petsi',
    version='0.1.0',
    url='https://github.com/vadaszd/petsi',
    project_urls={
        # "Bug Tracker": "...",
        # "Documentation": "...",
        "Source Code": "https://github.com/vadaszd/petsi",
    },
    classifiers=[
        "Development Status :: Alpha",
        "License :: OSI Approved :: MIT License"
        "Operating System :: OS Independent",
    ],
    license='MIT',
    author='vadaszd',
    author_email='',
    description='A Petri net simulator for performance modelling',
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="Petri net simulator performance modelling",

    python_requires='>=3.8',

    install_requires=["more-itertools>=8.2.0",
                      "graphviz~=0.14",
                      ],
    packages=find_packages(),
    package_data={
        'petsi': package_data,
    },

    zip_safe=False,

    **extension_args
)
