"""Setup and packaging for kubetest."""

import os
from codecs import open  # for consistent encoding

from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))

# Load the package's __init__.py file as a dictionary.
pkg = {}
with open(os.path.join(here, "kubetest", "__init__.py"), "r", "utf-8") as f:
    exec(f.read(), pkg)

# Load the README
readme = ""
if os.path.exists("README.md"):
    with open("README.md", "r", "utf-8") as f:
        readme = f.read()

setup(
    name=pkg["__title__"],
    version=pkg["__version__"],
    description=pkg["__description__"],
    long_description=readme,
    long_description_content_type="text/markdown",
    url=pkg["__url__"],
    author=pkg["__author__"],
    author_email=pkg["__author_email__"],
    license=pkg["__license__"],
    packages=find_packages(),
    python_requires=">=3.8",
    package_data={
        "": ["LICENSE"],
    },
    install_requires=[
        "kubernetes>=32, <33",
        "pyyaml>=5.4",
        "pytest",
    ],
    zip_safe=False,
    classifiers=[
        "Environment :: Plugins",
        "Framework :: Pytest",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    # this make a plugin available to pytest
    # https://docs.pytest.org/en/latest/writing_plugins.html#making-your-plugin-installable-by-others
    entry_points={"pytest11": ["kubetest = kubetest.plugin"]},
)
