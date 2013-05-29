#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import sys

try:
    from setuptools import setup, find_packages
except ImportError:
    from pkg import distribute_setup
    distribute_setup.use_setuptools()
    from setuptools import setup, find_packages
import os

from pkg import utils

import versioneer
versioneer.versionfile_source = 'src/leap/_version.py'
versioneer.versionfile_build = 'leap/_version.py'
versioneer.tag_prefix = ''  # tags are like 1.2.0
versioneer.parentdir_prefix = 'leap_client-'

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


cmdclass = versioneer.get_cmdclass()
leap_launcher = 'leap-client=leap.app:main'

setup(
    name="leap-client",
    package_dir={"": "src"},
    version=versioneer.get_version(),
    cmdclass=cmdclass,
    description="The Internet Encryption Toolkit",
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
    install_requires=utils.parse_requirements(),
    # Uncomment when tests are done
    test_suite='nose.collector',
    test_requires=utils.parse_requirements(
        reqfiles=['pkg/requirements-testing.pip']),
    keywords='LEAP, client, qt, encryption, proxy, openvpn, imap, smtp',
    author='The LEAP Encryption Access Project',
    author_email='info@leap.se',
    url='https://leap.se',
    license='GPL-3+',
    packages=find_packages(
        'src',
        exclude=['ez_setup', 'setup', 'examples', 'tests']),
    namespace_packages=["leap"],
    include_package_data=True,
    zip_safe=False,

    # not being used since setuptools does not like it.
    # looks like debhelper is honoring it...
    data_files=[
    #    ("share/man/man1",
    #        ["docs/man/leap-client.1"]),
        ("share/polkit-1/actions",
            ["pkg/linux/polkit/net.openvpn.gui.leap.policy"])
    ],
    platforms="all",
    entry_points={
        'console_scripts': [leap_launcher]
    },
)
