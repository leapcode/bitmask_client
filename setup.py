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

# get version from somewhere else
version = '0.1'

setup_root = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(setup_root, "src"))

setup(
    name='leap-client',
    package_dir={"": "src"},
    version=version,
    description="the internet encryption toolkit",
    long_description="""\
""",
    classifiers=[],  # Get strings from
    # http://pypi.python.org/pypi?%3Aaction=list_classifiers

    # XXX FIXME DEPS
    # deps: pyqt
    # test_deps: nose
    # build_deps: pyqt-utils

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
    install_requires=[
        # -*- Extra requirements: -*-
    ],
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
