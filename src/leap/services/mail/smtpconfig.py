# -*- coding: utf-8 -*-
# smtpconfig.py
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
SMTP configuration
"""
import logging

from leap.common.config.baseconfig import BaseConfig
from leap.services.mail.smtpspec import smtp_config_spec

logger = logging.getLogger(__name__)


class SMTPConfig(BaseConfig):
    """
    SMTP configuration abstraction class
    """

    def __init__(self):
        BaseConfig.__init__(self)

    def _get_spec(self):
        """
        Returns the spec object for the specific configuration
        """
        return smtp_config_spec

    def get_hosts(self):
        return self._safe_get_value("hosts")

    def get_locations(self):
        return self._safe_get_value("locations")

