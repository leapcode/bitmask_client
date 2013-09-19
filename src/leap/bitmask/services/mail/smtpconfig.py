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
import os

from leap.bitmask.config.providerconfig import ProviderConfig
from leap.bitmask.services import ServiceConfig
from leap.bitmask.services.mail.smtpspec import get_schema
from leap.bitmask.util import get_path_prefix
from leap.common.check import leap_assert, leap_assert_type

logger = logging.getLogger(__name__)


class SMTPConfig(ServiceConfig):
    """
    SMTP configuration abstraction class
    """
    _service_name = "smtp"

    def __init__(self):
        ServiceConfig.__init__(self)

    def _get_schema(self):
        """
        Returns the schema corresponding to the version given.

        :rtype: dict or None if the version is not supported.
        """
        return get_schema(self._api_version)

    def get_hosts(self):
        return self._safe_get_value("hosts")

    def get_locations(self):
        return self._safe_get_value("locations")

    def get_client_cert_path(self,
                             providerconfig=None,
                             about_to_download=False):
        """
        Returns the path to the certificate used by smtp
        """

        leap_assert(providerconfig, "We need a provider")
        leap_assert_type(providerconfig, ProviderConfig)

        cert_path = os.path.join(get_path_prefix(),
                                 "leap", "providers",
                                 providerconfig.get_domain(),
                                 "keys", "client", "smtp.pem")

        if not about_to_download:
            leap_assert(os.path.exists(cert_path),
                        "You need to download the certificate first")
            logger.debug("Using SMTP cert %s" % (cert_path,))

        return cert_path
