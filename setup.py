#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

try:
    from setuptools import setup, find_packages
except ImportError:
    #FIXME old?
    #use distribute_setup instead??
    #http://packages.python.org/distribute/setuptools.html#using-setuptools-without-bundling-it
    import ez_setup
    #XXX move ez_setup somewhere else?
    ez_setup.use_setuptools()
    from setuptools import setup, find_packages
import os

# XXX get version from somewhere else
version = '0.1.0'

setup_root = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(setup_root, "src"))

trove_classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: X11 Applications :: Qt",
    "Intended Audience :: End Users/Desktop",
    ("License :: OSI Approved :: GNU General "
     "Public License v3 or later (GPLv3+)"),
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2.6",
    "Programming Language :: Python :: 2.7",
    "Topic :: Communications",
    "Topic :: Security",
    "Topic :: System :: Networking",
    "Topic :: Utilities"
]

setup(
    name='leap-client',
    package_dir={"": "src"},
    version=version,
    description="the internet encryption toolkit",
    long_description=(
        "Desktop Client for the LEAP Platform."
        "\n"
        "LEAP (LEAP Encryption Access Project) develops "
        "a multi-year plan to secure everyday communication, breaking down"
        "into discrete services, to be rolled out one at a time.\n"
        "The client for the current phase gives support to the EIP Service."
        "EIP (the Encrypted Internet Proxy) provides circumvention, location "
        "anonymization, and traffic "
        "encryption in a hassle-free, automatically self-configuring fashion, "
        "and has an enhanced level of security."
    ),
    classifiers=trove_classifiers,

    # XXX FIXME DEPS
    # deps: pyqt

    # build_deps: pyqt-utils
    # XXX fixme move resource reloading
    # to this setup script.

    # XXX should implement a parse_requirements
    # and get them from the pip reqs. workaround needed
    # for argparse and <=2.6
    install_requires=[
        # -*- Extra requirements: -*-
        "configuration",
        "requests",
    ],
    test_suite='nose.collector',

    # XXX change to parse_test_requirements and
    # get them from pip reqs.
    test_requires=[
        "nose",
        "mock"],

    keywords='leap, client, qt, encryption',
    author='leap project',
    author_email='info@leap.se',
    url='http://leap.se',
    license='GPL',
    packages=find_packages(
        'src',
        exclude=['ez_setup', 'setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,

    # XXX platform switch
    data_files=[
        ("share/man/man1",
            ["docs/leap.1"]),
        ("share/polkit-1/actions",
            ["setup/linux/polkit/net.openvpn.gui.leap.policy"])
    ],
    platforms="all",
    scripts=["setup/scripts/leap"],
    entry_points="""
    # -*- Entry points: -*-
    """,
)
