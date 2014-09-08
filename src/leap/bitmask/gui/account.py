# -*- coding: utf-8 -*-
# Copyright (C) 2014 LEAP
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
A frontend GUI object to hold the current username and domain.
"""

from leap.bitmask.util import make_address
from leap.bitmask.config.leapsettings import LeapSettings
from leap.bitmask.services import EIP_SERVICE, MX_SERVICE

class Account():

    def __init__(self, username, domain):
        self._settings = LeapSettings()
        self.username = username
        self.domain = domain

        if self.username is not None:
          self.address = make_address(self.username, self.domain)
        else:
          self.address = self.domain

    def services(self):
        """
        returns a list of service name strings

        TODO: this should depend not just on the domain
        """
        return self._settings.get_enabled_services(self.domain)

    def is_email_enabled(self):
        MX_SERVICE in self.services()

    def is_eip_enabled(self):
        EIP_SERVICE in self.services()

