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

from leap.bitmask.config.providerconfig import ProviderConfig
from leap.bitmask.crypto.certs import download_client_cert
from leap.bitmask.services import download_service_config
from leap.bitmask.services.abstractbootstrapper import AbstractBootstrapper
from leap.common import certs as leap_certs
from leap.common.check import leap_assert, leap_assert_type
from leap.common.files import check_and_fix_urw_only

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

        download_service_config(
            self._provider_config,
            self._smtp_config,
            self._session,
            self._download_if_needed)

    def _download_client_certificates(self, *args):
        """
        Downloads the SMTP client certificate for the given provider

        We actually are downloading the certificate for the same uri as
        for the EIP config, but we duplicate these bits to allow mail
        service to be working in a provider that does not offer EIP.
        """
        # TODO factor out with eipboostrapper.download_client_certificates
        # TODO this shouldn't be a private method, it's called from
        # mainwindow.
        leap_assert(self._provider_config, "We need a provider configuration!")
        leap_assert(self._smtp_config, "We need an smtp configuration!")

        logger.debug("Downloading SMTP client certificate for %s" %
                     (self._provider_config.get_domain(),))

        client_cert_path = self._smtp_config.\
            get_client_cert_path(self._provider_config,
                                 about_to_download=True)

        # For re-download if something is wrong with the cert
        self._download_if_needed = self._download_if_needed and \
            not leap_certs.should_redownload(client_cert_path)

        if self._download_if_needed and \
                os.path.isfile(client_cert_path):
            check_and_fix_urw_only(client_cert_path)
            return

        download_client_cert(self._provider_config,
                             client_cert_path,
                             self._session)

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
