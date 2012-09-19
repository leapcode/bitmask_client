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
from pkg import branding
import versioneer
versioneer.versionfile_source = 'src/leap/_version.py'
versioneer.versionfile_build = 'leap/_version.py'
versioneer.tag_prefix = ''  # tags are like 1.2.0
#versioneer.parentdir_prefix = 'leap_client-'
versioneer.parentdir_prefix = branding.APP_PREFIX

branding.brandingfile = 'src/leap/_branding.py'
branding.brandingfile_build = 'leap/_branding.py'
branding.cert_path = 'src/leap/certs'

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

BRANDING_OPTS = """
# Do NOT manually edit this file!
# This file has been written from pkg/branding/config.py data by leap setup.py
# script.

BRANDING = {
    'short_name': "%(short_name)s",
    'provider_domain': "%(provider_domain)s",
    'provider_ca_file': "%(provider_ca_file)s"}
"""


def write_to_branding_file(filename, branding_dict):
    f = open(filename, "w")
    f.write(BRANDING_OPTS % branding_dict)
    f.close()


def copy_pemfile_to_certdir(frompath, topath):
    with open(frompath, "r") as cert_f:
        cert_s = cert_f.read()
    with open(topath, "w") as f:
        f.write(cert_s)


def do_branding(targetfile=branding.brandingfile):
    if branding.BRANDED_BUILD:
        opts = branding.BRANDED_OPTS
        print("DOING BRANDING FOR LEAP")
        certpath = opts['provider_ca_path']
        shortname = opts['short_name']
        tocertfile = shortname + '-cacert.pem'
        topath = os.path.join(
            branding.cert_path,
            tocertfile)
        copy_pemfile_to_certdir(
            certpath,
            topath)
        opts['provider_ca_file'] = tocertfile
        write_to_branding_file(
            targetfile,
            opts)
    else:
        print('not running branding because BRANDED_BUILD set to False')


from setuptools import Command


class DoBranding(Command):
    description = "copy the branding info the the top level package"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        do_branding()

from distutils.command.build import build as _build
from distutils.command.sdist import sdist as _sdist


class cmd_build(_build):
    def run(self):
        #versioneer.cmd_build(self)
        _build.run(self)

        # versioneer
        versions = versioneer.get_versions(verbose=True)
        # now locate _version.py in the new build/ directory and replace it
        # with an updated value
        target_versionfile = os.path.join(
            self.build_lib,
            versioneer.versionfile_build)
        print("UPDATING %s" % target_versionfile)
        os.unlink(target_versionfile)
        f = open(target_versionfile, "w")
        f.write(versioneer.SHORT_VERSION_PY % versions)
        f.close()

        # branding
        target_brandingfile = os.path.join(
            self.build_lib,
            branding.brandingfile_build)
        do_branding(targetfile=target_brandingfile)


class cmd_sdist(_sdist):
    def run(self):
        # versioneer:
        versions = versioneer.get_versions(verbose=True)
        self._versioneer_generated_versions = versions
        # unless we update this, the command will keep using the old version
        self.distribution.metadata.version = versions["version"]

        # branding:
        do_branding()
        return _sdist.run(self)

    def make_release_tree(self, base_dir, files):
        _sdist.make_release_tree(self, base_dir, files)
        # now locate _version.py in the new base_dir directory (remembering
        # that it may be a hardlink) and replace it with an updated value
        target_versionfile = os.path.join(
            base_dir, versioneer.versionfile_source)
        print("UPDATING %s" % target_versionfile)
        os.unlink(target_versionfile)
        f = open(target_versionfile, "w")
        f.write(
            versioneer.SHORT_VERSION_PY % self._versioneer_generated_versions)
        f.close()


cmdclass = versioneer.get_cmdclass()
cmdclass["branding"] = DoBranding
cmdclass["build"] = cmd_build
cmdclass["sdist"] = cmd_sdist

launcher_name = branding.get_shortname()
if launcher_name:
    leap_launcher = 'leap-%s-client=leap.app:main' % launcher_name
else:
    leap_launcher = 'leap=leap.app:main'

setup(
    name=branding.get_name(),
    package_dir={"": "src"},
    version=versioneer.get_version(),
    cmdclass=cmdclass,
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
    install_requires=utils.parse_requirements(),
    test_suite='nose.collector',
    test_requires=utils.parse_requirements(
        reqfiles=['pkg/test-requirements.pip']),
    keywords='leap, client, qt, encryption, proxy',
    author='The LEAP project',
    author_email='info@leap.se',
    url='https://leap.se',
    license='GPL',
    packages=find_packages(
        'src',
        exclude=['ez_setup', 'setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,

    # add platform switch
    data_files=[
        ("share/man/man1",
            ["docs/leap.1"]),
        ("share/polkit-1/actions",
            ["pkg/linux/polkit/net.openvpn.gui.leap.policy"])
    ],
    platforms="all",
    #scripts=["pkg/scripts/leap"],
    entry_points = {
        'console_scripts': [leap_launcher]
    },
    #entry_points="""
    # -*- Entry points: -*-
    #""",
)
