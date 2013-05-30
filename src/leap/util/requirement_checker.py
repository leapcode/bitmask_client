# -*- coding: utf-8 -*-
# requirement_checker.py
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
Utility to check the needed requirements.
"""

import os
import logging

from pkg_resources import (DistributionNotFound,
                           get_distribution,
                           Requirement,
                           resource_stream,
                           VersionConflict)

logger = logging.getLogger(__name__)


def get_requirements():
    """
    This function returns a list with requirements.
    It checks either if its running from the source or if its installed.

    :returns: a list with packages names, required for the app.
    :return type: list of str.
    """
    develop = True
    requirements = []

    try:
        # if we are running from the source
        from pkg import util
        requirements = util.parse_requirements()
    except ImportError:
        develop = False

    # if we are running from the package
    if not develop:
        requires_file_name = os.path.join('leap', 'util', 'reqs.txt')
        dist_name = Requirement.parse('leap-client')

        try:
            with resource_stream(dist_name, requires_file_name) as stream:
                requirements = [line.strip() for line in stream]
        except Exception, e:
            logger.error("Requirements file not found. %e", (e, ))

    return requirements


def check_requirements():
    """
    This function check the dependencies declared in the
    requirement(s) file(s) and logs the results.
    """
    logger.debug("Checking requirements...")
    requirements = get_requirements()

    for package in requirements:
        try:
            get_distribution(package)
        except VersionConflict:
            required_package = Requirement.parse(package)
            required_version = required_package.specs[0]
            required_name = required_package.key

            installed_package = get_distribution(required_name)
            installed_version = installed_package.version
            installed_location = installed_package.location

            msg = "Error: version not satisfied. "
            msg += "Expected %s, installed %s (path: %s)." % (
                required_version, installed_version, installed_location)

            result = "%s ... %s" % (package, msg)
            logger.error(result)
        except DistributionNotFound:
            msg = "Error: package not found!"
            result = "%s ... %s" % (package, msg)
            logger.error(result)
        else:
            msg = "OK"
            result = "%s ... %s" % (package, msg)
            logger.debug(result)

    logger.debug('Done')
