# -*- coding: utf-8 -*-
# providerbootstrapper.py
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
Provider bootstrapping
"""
import logging
import socket
import os

import requests

from PySide import QtCore

from leap.common.certs import get_digest
from leap.common.files import check_and_fix_urw_only, get_mtime, mkdir_p
from leap.common.check import leap_assert, leap_assert_type, leap_check
from leap.config.providerconfig import ProviderConfig, MissingCACert
from leap.util.request_helpers import get_content
from leap.util.constants import REQUEST_TIMEOUT
from leap.services.abstractbootstrapper import AbstractBootstrapper
from leap.provider.supportedapis import SupportedAPIs


logger = logging.getLogger(__name__)


class UnsupportedProviderAPI(Exception):
    """
    Raised when attempting to use a provider with an incompatible API.
    """
    pass


class WrongFingerprint(Exception):
    """
    Raised when a fingerprint comparison does not match.
    """
    pass


class ProviderBootstrapper(AbstractBootstrapper):
    """
    Given a provider URL performs a series of checks and emits signals
    after they are passed.
    If a check fails, the subsequent checks are not executed
    """

    # All dicts returned are of the form
    # {"passed": bool, "error": str}
    name_resolution = QtCore.Signal(dict)
    https_connection = QtCore.Signal(dict)
    download_provider_info = QtCore.Signal(dict)

    download_ca_cert = QtCore.Signal(dict)
    check_ca_fingerprint = QtCore.Signal(dict)
    check_api_certificate = QtCore.Signal(dict)

    def __init__(self, bypass_checks=False):
        """
        Constructor for provider bootstrapper object

        :param bypass_checks: Set to true if the app should bypass
        first round of checks for CA certificates at bootstrap
        :type bypass_checks: bool
        """
        AbstractBootstrapper.__init__(self, bypass_checks)

        self._domain = None
        self._provider_config = None
        self._download_if_needed = False

    def _check_name_resolution(self):
        """
        Checks that the name resolution for the provider name works
        """
        leap_assert(self._domain, "Cannot check DNS without a domain")

        logger.debug("Checking name resolution for %s" % (self._domain))

        # We don't skip this check, since it's basic for the whole
        # system to work
        socket.gethostbyname(self._domain)

    def _check_https(self, *args):
        """
        Checks that https is working and that the provided certificate
        checks out
        """

        leap_assert(self._domain, "Cannot check HTTPS without a domain")

        logger.debug("Checking https for %s" % (self._domain))

        # We don't skip this check, since it's basic for the whole
        # system to work

        try:
            res = self._session.get("https://%s" % (self._domain,),
                                    verify=not self._bypass_checks,
                                    timeout=REQUEST_TIMEOUT)
            res.raise_for_status()
        except requests.exceptions.SSLError:
            self._err_msg = self.tr("Provider certificate could "
                                    "not be verified")
            raise
        except Exception:
            self._err_msg = self.tr("Provider does not support HTTPS")
            raise

    def _download_provider_info(self, *args):
        """
        Downloads the provider.json defition
        """
        leap_assert(self._domain,
                    "Cannot download provider info without a domain")

        logger.debug("Downloading provider info for %s" % (self._domain))

        headers = {}

        provider_json = os.path.join(
            ProviderConfig().get_path_prefix(), "leap", "providers",
            self._domain, "provider.json")
        mtime = get_mtime(provider_json)

        if self._download_if_needed and mtime:
            headers['if-modified-since'] = mtime

        uri = "https://%s/%s" % (self._domain, "provider.json")
        verify = not self._bypass_checks

        if mtime:  # the provider.json exists
            provider_config = ProviderConfig()
            provider_config.load(provider_json)
            try:
                verify = provider_config.get_ca_cert_path()
                uri = provider_config.get_api_uri() + '/provider.json'
            except MissingCACert:
                # get_ca_cert_path fails if the certificate does not exists.
                pass

        logger.debug("Requesting for provider.json... "
                     "uri: {0}, verify: {1}, headers: {2}".format(
                         uri, verify, headers))
        res = self._session.get(uri, verify=verify,
                                headers=headers, timeout=REQUEST_TIMEOUT)
        res.raise_for_status()
        logger.debug("Request status code: {0}".format(res.status_code))

        # Not modified
        if res.status_code == 304:
            logger.debug("Provider definition has not been modified")
        else:
            provider_definition, mtime = get_content(res)

            provider_config = ProviderConfig()
            provider_config.load(data=provider_definition, mtime=mtime)
            provider_config.save(["leap",
                                  "providers",
                                  self._domain,
                                  "provider.json"])

            api_version = provider_config.get_api_version()
            if SupportedAPIs.supports(api_version):
                logger.debug("Provider definition has been modified")
            else:
                api_supported = ', '.join(SupportedAPIs.SUPPORTED_APIS)
                error = ('Unsupported provider API version. '
                         'Supported versions are: {}. '
                         'Found: {}.').format(api_supported, api_version)

                logger.error(error)
                raise UnsupportedProviderAPI(error)

    def run_provider_select_checks(self, domain, download_if_needed=False):
        """
        Populates the check queue.

        :param domain: domain to check
        :type domain: str

        :param download_if_needed: if True, makes the checks do not
                                   overwrite already downloaded data
        :type download_if_needed: bool
        """
        leap_assert(domain and len(domain) > 0, "We need a domain!")

        self._domain = ProviderConfig.sanitize_path_component(domain)
        self._download_if_needed = download_if_needed

        cb_chain = [
            (self._check_name_resolution, self.name_resolution),
            (self._check_https, self.https_connection),
            (self._download_provider_info, self.download_provider_info)
        ]

        return self.addCallbackChain(cb_chain)

    def _should_proceed_cert(self):
        """
        Returns False if the certificate already exists for the given
        provider. True otherwise

        :rtype: bool
        """
        leap_assert(self._provider_config, "We need a provider config!")

        if not self._download_if_needed:
            return True

        return not os.path.exists(self._provider_config
                                  .get_ca_cert_path(about_to_download=True))

    def _download_ca_cert(self, *args):
        """
        Downloads the CA cert that is going to be used for the api URL
        """

        leap_assert(self._provider_config, "Cannot download the ca cert "
                    "without a provider config!")

        logger.debug("Downloading ca cert for %s at %s" %
                     (self._domain, self._provider_config.get_ca_cert_uri()))

        if not self._should_proceed_cert():
            check_and_fix_urw_only(
                self._provider_config
                .get_ca_cert_path(about_to_download=True))
            return

        res = self._session.get(self._provider_config.get_ca_cert_uri(),
                                verify=not self._bypass_checks,
                                timeout=REQUEST_TIMEOUT)
        res.raise_for_status()

        cert_path = self._provider_config.get_ca_cert_path(
            about_to_download=True)
        cert_dir = os.path.dirname(cert_path)
        mkdir_p(cert_dir)
        with open(cert_path, "w") as f:
            f.write(res.content)

        check_and_fix_urw_only(cert_path)

    def _check_ca_fingerprint(self, *args):
        """
        Checks the CA cert fingerprint against the one provided in the
        json definition
        """
        leap_assert(self._provider_config, "Cannot check the ca cert "
                    "without a provider config!")

        logger.debug("Checking ca fingerprint for %s and cert %s" %
                     (self._domain,
                      self._provider_config.get_ca_cert_path()))

        if not self._should_proceed_cert():
            return

        parts = self._provider_config.get_ca_cert_fingerprint().split(":")

        error_msg = "Wrong fingerprint format"
        leap_check(len(parts) == 2, error_msg, WrongFingerprint)

        method = parts[0].strip()
        fingerprint = parts[1].strip()
        cert_data = None
        with open(self._provider_config.get_ca_cert_path()) as f:
            cert_data = f.read()

        leap_assert(len(cert_data) > 0, "Could not read certificate data")
        digest = get_digest(cert_data, method)

        error_msg = "Downloaded certificate has a different fingerprint!"
        leap_check(digest == fingerprint, error_msg, WrongFingerprint)

    def _check_api_certificate(self, *args):
        """
        Tries to make an API call with the downloaded cert and checks
        if it validates against it
        """
        leap_assert(self._provider_config, "Cannot check the ca cert "
                    "without a provider config!")

        logger.debug("Checking api certificate for %s and cert %s" %
                     (self._provider_config.get_api_uri(),
                      self._provider_config.get_ca_cert_path()))

        if not self._should_proceed_cert():
            return

        test_uri = "%s/%s/cert" % (self._provider_config.get_api_uri(),
                                   self._provider_config.get_api_version())
        res = self._session.get(test_uri,
                                verify=self._provider_config
                                .get_ca_cert_path(),
                                timeout=REQUEST_TIMEOUT)
        res.raise_for_status()

    def run_provider_setup_checks(self,
                                  provider_config,
                                  download_if_needed=False):
        """
        Starts the checks needed for a new provider setup.

        :param provider_config: Provider configuration
        :type provider_config: ProviderConfig

        :param download_if_needed: if True, makes the checks do not
                                   overwrite already downloaded data.
        :type download_if_needed: bool
        """
        leap_assert(provider_config, "We need a provider config!")
        leap_assert_type(provider_config, ProviderConfig)

        self._provider_config = provider_config
        self._download_if_needed = download_if_needed

        cb_chain = [
            (self._download_ca_cert, self.download_ca_cert),
            (self._check_ca_fingerprint, self.check_ca_fingerprint),
            (self._check_api_certificate, self.check_api_certificate)
        ]

        return self.addCallbackChain(cb_chain)
