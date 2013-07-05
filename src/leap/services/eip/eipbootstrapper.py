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

from PySide import QtCore

from leap.common.check import leap_assert, leap_assert_type
from leap.common import certs
from leap.common.files import check_and_fix_urw_only, get_mtime, mkdir_p
from leap.config.providerconfig import ProviderConfig
from leap.crypto.srpauth import SRPAuth
from leap.services.eip.eipconfig import EIPConfig
from leap.util.request_helpers import get_content
from leap.util.constants import REQUEST_TIMEOUT
from leap.services.abstractbootstrapper import AbstractBootstrapper

logger = logging.getLogger(__name__)


class EIPBootstrapper(AbstractBootstrapper):
    """
    Sets up EIP for a provider a series of checks and emits signals
    after they are passed.
    If a check fails, the subsequent checks are not executed
    """

    # All dicts returned are of the form
    # {"passed": bool, "error": str}
    download_config = QtCore.Signal(dict)
    download_client_certificate = QtCore.Signal(dict)

    def __init__(self):
        AbstractBootstrapper.__init__(self)

        self._provider_config = None
        self._eip_config = None
        self._download_if_needed = False

    def _download_config(self, *args):
        """
        Downloads the EIP config for the given provider
        """

        leap_assert(self._provider_config,
                    "We need a provider configuration!")

        logger.debug("Downloading EIP config for %s" %
                     (self._provider_config.get_domain(),))

        self._eip_config = EIPConfig()

        headers = {}
        mtime = get_mtime(os.path.join(self._eip_config
                                       .get_path_prefix(),
                                       "leap",
                                       "providers",
                                       self._provider_config.get_domain(),
                                       "eip-service.json"))

        if self._download_if_needed and mtime:
            headers['if-modified-since'] = mtime

        # there is some confusion with this uri,
        # it's in 1/config/eip, config/eip and config/1/eip...
        config_uri = "%s/%s/config/eip-service.json" % (
            self._provider_config.get_api_uri(),
            self._provider_config.get_api_version())
        logger.debug('Downloading eip config from: %s' % config_uri)

        res = self._session.get(config_uri,
                                verify=self._provider_config
                                .get_ca_cert_path(),
                                headers=headers,
                                timeout=REQUEST_TIMEOUT)
        res.raise_for_status()

        # Not modified
        if res.status_code == 304:
            logger.debug("EIP definition has not been modified")
        else:
            eip_definition, mtime = get_content(res)

            self._eip_config.load(data=eip_definition, mtime=mtime)
            self._eip_config.save(["leap",
                                   "providers",
                                   self._provider_config.get_domain(),
                                   "eip-service.json"])

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
            not certs.should_redownload(client_cert_path)

        if self._download_if_needed and \
                os.path.exists(client_cert_path):
            check_and_fix_urw_only(client_cert_path)
            return

        srp_auth = SRPAuth(self._provider_config)
        session_id = srp_auth.get_session_id()
        cookies = None
        if session_id:
            cookies = {"_session_id": session_id}
        cert_uri = "%s/%s/cert" % (
            self._provider_config.get_api_uri(),
            self._provider_config.get_api_version())
        logger.debug('getting cert from uri: %s' % cert_uri)
        res = self._session.get(cert_uri,
                                verify=self._provider_config
                                .get_ca_cert_path(),
                                cookies=cookies,
                                timeout=REQUEST_TIMEOUT)
        res.raise_for_status()
        client_cert = res.content

        if not certs.is_valid_pemfile(client_cert):
            raise Exception(self.tr("The downloaded certificate is not a "
                                    "valid PEM file"))

        mkdir_p(os.path.dirname(client_cert_path))

        with open(client_cert_path, "w") as f:
            f.write(client_cert)

        check_and_fix_urw_only(client_cert_path)

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
            (self._download_config, self.download_config),
            (self._download_client_certificates,
             self.download_client_certificate)
        ]

        return self.addCallbackChain(cb_chain)
