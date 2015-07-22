# -*- coding: utf-8 -*-
# utils.py
# Copyright (C) 2013 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Utils to help in the setup process
"""
import os
import re
import sys


def is_develop_mode():
    """
    Returns True if we're calling the setup script using the argument for
    setuptools development mode.

    This avoids messing up with dependency pinning and order, the
    responsibility of installing the leap dependencies is left to the
    developer.
    """
    args = sys.argv
    devflags = "setup.py", "develop"
    if (args[0], args[1]) == devflags:
        return True
    return False


def get_reqs_from_files(reqfiles):
    """
    Returns the contents of the top requirement file listed as a
    string list with the lines

    @param reqfiles: requirement files to parse
    @type reqfiles: list of str
    """
    for reqfile in reqfiles:
        if os.path.isfile(reqfile):
            return open(reqfile, 'r').read().split('\n')


def parse_requirements(reqfiles=['requirements.txt',
                                 'requirements.pip',
                                 'pkg/requirements.pip']):
    """
    Parses the requirement files provided.

    Checks the value of LEAP_VENV_SKIP_PYSIDE to see if it should
    return PySide as a dep or not. Don't set, or set to 0 if you want
    to install it through pip.

    @param reqfiles: requirement files to parse
    @type reqfiles: list of str
    """

    requirements = []
    skip_pyside = os.getenv("LEAP_VENV_SKIP_PYSIDE", "0") != "0"
    for line in get_reqs_from_files(reqfiles):
        # -e git://foo.bar/baz/master#egg=foobar
        if re.match(r'\s*-e\s+', line):
            pass
            # do not try to do anything with externals on vcs
            #requirements.append(re.sub(r'\s*-e\s+.*#egg=(.*)$', r'\1',
                                #line))
        # http://foo.bar/baz/foobar/zipball/master#egg=foobar
        elif re.match(r'\s*https?:', line):
            requirements.append(re.sub(r'\s*https?:.*#egg=(.*)$', r'\1',
                                line))
        # -f lines are for index locations, and don't get used here
        elif re.match(r'\s*-f\s+', line):
            pass

        # argparse is part of the standard library starting with 2.7
        # adding it to the requirements list screws distro installs
        elif line == 'argparse' and sys.version_info >= (2, 7):
            pass
        elif line == 'PySide' and skip_pyside:
            pass
        # do not include comments
        elif line.lstrip().startswith('#'):
            pass
        else:
            if line != '':
                requirements.append(line)

    return requirements
