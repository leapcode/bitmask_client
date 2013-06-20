# -*- coding: utf-8 -*-
# __init__.py
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
Services module.
"""
NOT_YET_DEPLOYED = ["mx"]  # for 0.2.2 release


def get_available(services):
    """
    Returns a list of the available services.

    :param services: a list containing the services to be filtered.
    :type services: list of str

    :returns: a list of the available services
    :rtype: list of str
    """
    return filter(lambda s: s not in NOT_YET_DEPLOYED, services)
