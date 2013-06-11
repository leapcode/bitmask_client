# -*- coding: utf-8 -*-
# supportedapis.py
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
API Support check.
"""


class SupportedAPIs(object):
    """
    Class responsible of checking for API compatibility.
    """
    SUPPORTED_APIS = ["1"]

    @classmethod
    def supports(self, api_version):
        """
        :param api_version: the version number of the api that we need to check
        :type api_version: str

        :returns: if that version is supported or not.
        :return type: bool
        """
        return api_version in self.SUPPORTED_APIS
