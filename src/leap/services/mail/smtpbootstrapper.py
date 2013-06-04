# -*- coding: utf-8 -*-
# smtpbootstrapper.py
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
SMTP bootstrapping
"""

import logging
import os

from PySide import QtCore

from leap.common.check import leap_assert, leap_assert_type
from leap.common.files import get_mtime
from leap.config.providerconfig import ProviderConfig
from leap.crypto.srpauth import SRPAuth
from leap.util.request_helpers import get_content
from leap.services.abstractbootstrapper import AbstractBootstrapper

logger = logging.getLogger(__name__)


class SMTPBootstrapper(AbstractBootstrapper):
    """
    SMTP init procedure
    """

    # All dicts returned are of the form
    # {"passed": bool, "error": str}
    download_config = QtCore.Signal(dict)

    def __init__(self):
        AbstractBootstrapper.__init__(self)

        self._provider_config = None
        self._smtp_config = None
        self._download_if_needed = False

    def _download_config(self, *args):
        """
        Downloads the SMTP config for the given provider
        """

        leap_assert(self._provider_config,
                    "We need a provider configuration!")

        logger.debug("Downloading SMTP config for %s" %
                     (self._provider_config.get_domain(),))

        headers = {}
        mtime = get_mtime(os.path.join(self._smtp_config
                                       .get_path_prefix(),
                                       "leap",
                                       "providers",
                                       self._provider_config.get_domain(),
                                       "smtp-service.json"))

        if self._download_if_needed and mtime:
            headers['if-modified-since'] = mtime

        # there is some confusion with this uri,
        config_uri = "%s/%s/config/smtp-service.json" % (
            self._provider_config.get_api_uri(),
            self._provider_config.get_api_version())
        logger.debug('Downloading SMTP config from: %s' % config_uri)

        srp_auth = SRPAuth(self._provider_config)
        session_id = srp_auth.get_session_id()
        cookies = None
        if session_id:
            cookies = {"_session_id": session_id}

        res = self._session.get(config_uri,
                                verify=self._provider_config
                                .get_ca_cert_path(),
                                headers=headers,
                                cookies=cookies)
        res.raise_for_status()

        # Not modified
        if res.status_code == 304:
            logger.debug("SMTP definition has not been modified")
            self._smtp_config.load(os.path.join("leap",
                                                "providers",
                                                self._provider_config.\
                                                    get_domain(),
                                                "smtp-service.json"))
        else:
            smtp_definition, mtime = get_content(res)

            self._smtp_config.load(data=smtp_definition, mtime=mtime)
            self._smtp_config.save(["leap",
                                    "providers",
                                    self._provider_config.get_domain(),
                                    "smtp-service.json"])

    def run_smtp_setup_checks(self,
                              provider_config,
                              smtp_config,
                              download_if_needed=False):
        """
        Starts the checks needed for a new smtp setup

        :param provider_config: Provider configuration
        :type provider_config: ProviderConfig
        :param smtp_config: SMTP configuration to populate
        :type smtp_config: SMTPConfig
        :param download_if_needed: True if it should check for mtime
                                   for the file
        :type download_if_needed: bool
        """
        leap_assert_type(provider_config, ProviderConfig)

        self._provider_config = provider_config
        self._smtp_config = smtp_config
        self._download_if_needed = download_if_needed

        cb_chain = [
            (self._download_config, self.download_config),
        ]

        self.addCallbackChain(cb_chain)
