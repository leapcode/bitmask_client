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

from PySide import QtGui, QtCore

from leap.common.certs import get_digest
from leap.common.files import check_and_fix_urw_only, get_mtime, mkdir_p
from leap.common.check import leap_assert, leap_assert_type
from leap.config.providerconfig import ProviderConfig
from leap.util.checkerthread import CheckerThread
from leap.util.request_helpers import get_content

logger = logging.getLogger(__name__)


class ProviderBootstrapper(QtCore.QObject):
    """
    Given a provider URL performs a series of checks and emits signals
    after they are passed.
    If a check fails, the subsequent checks are not executed
    """

    PASSED_KEY = "passed"
    ERROR_KEY = "error"

    IDLE_SLEEP_INTERVAL = 100

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

        @param bypass_checks: Set to true if the app should bypass
        first round of checks for CA certificates at bootstrap
        @type bypass_checks: bool
        """
        QtCore.QObject.__init__(self)

        # **************************************************** #
        # Dependency injection helpers, override this for more
        # granular testing
        self._fetcher = requests
        # **************************************************** #

        self._session = self._fetcher.session()
        self._domain = None
        self._provider_config = None
        self._download_if_needed = False
        self._bypass_checks = bypass_checks

    def _check_name_resolution(self):
        """
        Checks that the name resolution for the provider name works

        @return: True if the checks passed, False otherwise
        @rtype: bool
        """

        leap_assert(self._domain, "Cannot check DNS without a domain")

        logger.debug("Checking name resolution for %s" % (self._domain))

        name_resolution_data = {
            self.PASSED_KEY: False,
            self.ERROR_KEY: ""
        }

        # We don't skip this check, since it's basic for the whole
        # system to work
        try:
            socket.gethostbyname(self._domain)
            name_resolution_data[self.PASSED_KEY] = True
        except socket.gaierror as e:
            name_resolution_data[self.ERROR_KEY] = "%s" % (e,)

        logger.debug("Emitting name_resolution %s" % (name_resolution_data,))
        self.name_resolution.emit(name_resolution_data)

        return name_resolution_data[self.PASSED_KEY]

    def _check_https(self):
        """
        Checks that https is working and that the provided certificate
        checks out

        @return: True if the checks passed, False otherwise
        @rtype: bool
        """

        leap_assert(self._domain, "Cannot check HTTPS without a domain")

        logger.debug("Checking https for %s" % (self._domain))

        https_data = {
            self.PASSED_KEY: False,
            self.ERROR_KEY: ""
        }

        # We don't skip this check, since it's basic for the whole
        # system to work

        try:
            res = self._session.get("https://%s" % (self._domain,),
                                    verify=not self._bypass_checks)
            res.raise_for_status()
            https_data[self.PASSED_KEY] = True
        except requests.exceptions.SSLError as e:
            logger.error("%s" % (e,))
            https_data[self.ERROR_KEY] = self.tr("Provider certificate could "
                                                 "not verify")
        except Exception as e:
            logger.error("%s" % (e,))
            https_data[self.ERROR_KEY] = self.tr("Provider does not support "
                                                 "HTTPS")

        logger.debug("Emitting https_connection %s" % (https_data,))
        self.https_connection.emit(https_data)

        return https_data[self.PASSED_KEY]

    def _download_provider_info(self):
        """
        Downloads the provider.json defition

        @return: True if the checks passed, False otherwise
        @rtype: bool
        """
        leap_assert(self._domain,
                    "Cannot download provider info without a domain")

        logger.debug("Downloading provider info for %s" % (self._domain))

        download_data = {
            self.PASSED_KEY: False,
            self.ERROR_KEY: ""
        }

        try:
            headers = {}
            mtime = get_mtime(os.path.join(ProviderConfig()
                                           .get_path_prefix(),
                                           "leap",
                                           "providers",
                                           self._domain,
                                           "provider.json"))
            if self._download_if_needed and mtime:
                headers['if-modified-since'] = mtime

            res = self._session.get("https://%s/%s" % (self._domain,
                                                       "provider.json"),
                                    headers=headers,
                                    verify=not self._bypass_checks)
            res.raise_for_status()

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

            download_data[self.PASSED_KEY] = True
        except Exception as e:
            download_data[self.ERROR_KEY] = "%s" % (e,)

        logger.debug("Emitting download_provider_info %s" % (download_data,))
        self.download_provider_info.emit(download_data)

        return download_data[self.PASSED_KEY]

    def run_provider_select_checks(self, checker,
                                   domain, download_if_needed=False):
        """
        Populates the check queue

        @param checker: checker thread to be used to run this check
        @type checker: CheckerThread
        @param domain: domain to check
        @type domain: str
        @param download_if_needed: if True, makes the checks do not
        overwrite already downloaded data
        @type download_if_needed: bool

        @return: True if the checks passed, False otherwise
        @rtype: bool
        """
        leap_assert(domain and len(domain) > 0, "We need a domain!")

        self._domain = domain
        self._download_if_needed = download_if_needed

        checker.add_checks([
            self._check_name_resolution,
            self._check_https,
            self._download_provider_info
        ])

    def _should_proceed_cert(self):
        """
        Returns False if the certificate already exists for the given
        provider. True otherwise

        @rtype: bool
        """
        leap_assert(self._provider_config, "We need a provider config!")

        if not self._download_if_needed:
            return True

        return not os.path.exists(self._provider_config
                                  .get_ca_cert_path(about_to_download=True))

    def _download_ca_cert(self):
        """
        Downloads the CA cert that is going to be used for the api URL

        @return: True if the checks passed, False otherwise
        @rtype: bool
        """

        leap_assert(self._provider_config, "Cannot download the ca cert "
                    "without a provider config!")

        logger.debug("Downloading ca cert for %s at %s" %
                     (self._domain, self._provider_config.get_ca_cert_uri()))

        download_ca_cert_data = {
            self.PASSED_KEY: False,
            self.ERROR_KEY: ""
        }

        if not self._should_proceed_cert():
            try:
                check_and_fix_urw_only(
                    self._provider_config
                    .get_ca_cert_path(about_to_download=True))
                download_ca_cert_data[self.PASSED_KEY] = True
            except Exception as e:
                download_ca_cert_data[self.PASSED_KEY] = False
                download_ca_cert_data[self.ERROR_KEY] = "%s" % (e,)
            self.download_ca_cert.emit(download_ca_cert_data)
            return download_ca_cert_data[self.PASSED_KEY]

        try:
            res = self._session.get(self._provider_config.get_ca_cert_uri(),
                                    verify=not self._bypass_checks)
            res.raise_for_status()

            cert_path = self._provider_config.get_ca_cert_path(
                about_to_download=True)

            cert_dir = os.path.dirname(cert_path)

            mkdir_p(cert_dir)

            with open(cert_path, "w") as f:
                f.write(res.content)

            check_and_fix_urw_only(cert_path)

            download_ca_cert_data[self.PASSED_KEY] = True
        except Exception as e:
            download_ca_cert_data[self.ERROR_KEY] = "%s" % (e,)

        logger.debug("Emitting download_ca_cert %s" % (download_ca_cert_data,))
        self.download_ca_cert.emit(download_ca_cert_data)

        return download_ca_cert_data[self.PASSED_KEY]

    def _check_ca_fingerprint(self):
        """
        Checks the CA cert fingerprint against the one provided in the
        json definition

        @return: True if the checks passed, False otherwise
        @rtype: bool
        """
        leap_assert(self._provider_config, "Cannot check the ca cert "
                    "without a provider config!")

        logger.debug("Checking ca fingerprint for %s and cert %s" %
                     (self._domain,
                      self._provider_config.get_ca_cert_path()))

        check_ca_fingerprint_data = {
            self.PASSED_KEY: False,
            self.ERROR_KEY: ""
        }

        if not self._should_proceed_cert():
            check_ca_fingerprint_data[self.PASSED_KEY] = True
            self.check_ca_fingerprint.emit(check_ca_fingerprint_data)
            return True

        try:
            parts = self._provider_config.get_ca_cert_fingerprint().split(":")
            leap_assert(len(parts) == 2, "Wrong fingerprint format")

            method = parts[0].strip()
            fingerprint = parts[1].strip()
            cert_data = None
            with open(self._provider_config.get_ca_cert_path()) as f:
                cert_data = f.read()

            leap_assert(len(cert_data) > 0, "Could not read certificate data")

            digest = get_digest(cert_data, method)

            leap_assert(digest == fingerprint,
                        "Downloaded certificate has a different fingerprint!")

            check_ca_fingerprint_data[self.PASSED_KEY] = True
        except Exception as e:
            check_ca_fingerprint_data[self.ERROR_KEY] = "%s" % (e,)

        logger.debug("Emitting check_ca_fingerprint %s" %
                     (check_ca_fingerprint_data,))
        self.check_ca_fingerprint.emit(check_ca_fingerprint_data)

        return check_ca_fingerprint_data[self.PASSED_KEY]

    def _check_api_certificate(self):
        """
        Tries to make an API call with the downloaded cert and checks
        if it validates against it

        @return: True if the checks passed, False otherwise
        @rtype: bool
        """
        leap_assert(self._provider_config, "Cannot check the ca cert "
                    "without a provider config!")

        logger.debug("Checking api certificate for %s and cert %s" %
                     (self._provider_config.get_api_uri(),
                      self._provider_config.get_ca_cert_path()))

        check_api_certificate_data = {
            self.PASSED_KEY: False,
            self.ERROR_KEY: ""
        }

        if not self._should_proceed_cert():
            check_api_certificate_data[self.PASSED_KEY] = True
            self.check_api_certificate.emit(check_api_certificate_data)
            return True

        try:
            test_uri = "%s/%s/cert" % (self._provider_config.get_api_uri(),
                                       self._provider_config.get_api_version())
            res = self._session.get(test_uri,
                                    verify=self._provider_config
                                    .get_ca_cert_path())
            res.raise_for_status()
            check_api_certificate_data[self.PASSED_KEY] = True
        except Exception as e:
            check_api_certificate_data[self.ERROR_KEY] = "%s" % (e,)

        logger.debug("Emitting check_api_certificate %s" %
                     (check_api_certificate_data,))
        self.check_api_certificate.emit(check_api_certificate_data)

        return check_api_certificate_data[self.PASSED_KEY]

    def run_provider_setup_checks(self, checker,
                                  provider_config,
                                  download_if_needed=False):
        """
        Starts the checks needed for a new provider setup

        @param provider_config: Provider configuration
        @type provider_config: ProviderConfig
        @param download_if_needed: if True, makes the checks do not
        overwrite already downloaded data
        @type download_if_needed: bool
        """
        leap_assert(provider_config, "We need a provider config!")
        leap_assert_type(provider_config, ProviderConfig)

        self._provider_config = provider_config
        self._download_if_needed = download_if_needed

        checker.add_checks([
            self._download_ca_cert,
            self._check_ca_fingerprint,
            self._check_api_certificate
        ])

if __name__ == "__main__":
    import sys
    from functools import partial
    app = QtGui.QApplication(sys.argv)

    import signal

    def sigint_handler(*args, **kwargs):
        logger.debug('SIGINT catched. shutting down...')
        bootstrapper_checks = args[0]
        bootstrapper_checks.set_should_quit()
        QtGui.QApplication.quit()

    def signal_tester(d):
        print d

    logger = logging.getLogger(name='leap')
    logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s '
        '- %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)

    bootstrapper_checks = ProviderBootstrapper()

    checker = CheckerThread()
    checker.start()

    sigint = partial(sigint_handler, checker)
    signal.signal(signal.SIGINT, sigint)

    timer = QtCore.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)
    app.connect(app, QtCore.SIGNAL("aboutToQuit()"),
                checker.set_should_quit)
    w = QtGui.QWidget()
    w.resize(100, 100)
    w.show()

    bootstrapper_checks.run_provider_select_checks(checker,
                                                   "bitmask.net")

    provider_config = ProviderConfig()
    if provider_config.load(os.path.join("leap",
                                         "providers",
                                         "bitmask.net",
                                         "provider.json")):
        bootstrapper_checks.run_provider_setup_checks(checker,
                                                      provider_config)

    sys.exit(app.exec_())
