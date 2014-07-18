# -*- coding: utf-8 -*-
# eipbootstrapper.py
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
EIP bootstrapping
"""
import logging
import os

from leap.bitmask.config.providerconfig import ProviderConfig
from leap.bitmask.crypto.certs import download_client_cert
from leap.bitmask.services import download_service_config
from leap.bitmask.services.abstractbootstrapper import AbstractBootstrapper
from leap.bitmask.services.eip.eipconfig import EIPConfig
from leap.common import certs as leap_certs
from leap.common.check import leap_assert, leap_assert_type
from leap.common.files import check_and_fix_urw_only

logger = logging.getLogger(__name__)


class EIPBootstrapper(AbstractBootstrapper):
    """
    Sets up EIP for a provider a series of checks and emits signals
    after they are passed.
    If a check fails, the subsequent checks are not executed
    """

    def __init__(self, signaler=None):
        """
        Constructor for the EIP bootstrapper object

        :param signaler: Signaler object used to receive notifications
                         from the backend
        :type signaler: Signaler
        """
        AbstractBootstrapper.__init__(self, signaler)

        self._provider_config = None
        self._eip_config = None
        self._download_if_needed = False
        if signaler is not None:
            self._cancel_signal = signaler.eip_cancelled_setup

    def _download_config(self, *args):
        """
        Downloads the EIP config for the given provider
        """

        leap_assert(self._provider_config,
                    "We need a provider configuration!")
        logger.debug("Downloading EIP config for %s" %
                     (self._provider_config.get_domain(),))

        self._eip_config = EIPConfig()
        download_service_config(
            self._provider_config,
            self._eip_config,
            self._session,
            self._download_if_needed)

    def _download_client_certificates(self, *args):
        """
        Downloads the EIP client certificate for the given provider
        """
        leap_assert(self._provider_config, "We need a provider configuration!")
        leap_assert(self._eip_config, "We need an eip configuration!")

        logger.debug("Downloading EIP client certificate for %s" %
                     (self._provider_config.get_domain(),))

        client_cert_path = self._eip_config.\
            get_client_cert_path(self._provider_config,
                                 about_to_download=True)

        # For re-download if something is wrong with the cert
        self._download_if_needed = self._download_if_needed and \
            not leap_certs.should_redownload(client_cert_path)

        if self._download_if_needed and \
                os.path.isfile(client_cert_path):
            check_and_fix_urw_only(client_cert_path)
            return

        download_client_cert(
            self._provider_config,
            client_cert_path,
            self._session)

    def run_eip_setup_checks(self,
                             provider_config,
                             download_if_needed=False):
        """
        Starts the checks needed for a new eip setup

        :param provider_config: Provider configuration
        :type provider_config: ProviderConfig
        """
        leap_assert(provider_config, "We need a provider config!")
        leap_assert_type(provider_config, ProviderConfig)

        self._provider_config = provider_config
        self._download_if_needed = download_if_needed

        cb_chain = [
            (self._download_config, self._signaler.eip_config_ready),
            (self._download_client_certificates,
             self._signaler.eip_client_certificate_ready)
        ]

        return self.addCallbackChain(cb_chain)
