from setuptools import setup

from mnemon.constants import __version__

DESC = """A simple cache interface for Python objects. Abuse it."""


setup(
    name="mnemon",
    version=__version__,
    author="myyc",
    description="A simple cache interface for Python objects",
    license="BSD",
    keywords="python cache redis",
    packages=["mnemon"],
    long_description=DESC,
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
    ],
    install_requires=["redis"],
)
