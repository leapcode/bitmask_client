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

import requests
import logging
import os
import errno

from PySide import QtGui, QtCore

from leap.crypto.srpauth import SRPAuth
from leap.config.providerconfig import ProviderConfig
from leap.services.eip.eipconfig import EIPConfig
from leap.util.check import leap_assert, leap_assert_type
from leap.util.checkerthread import CheckerThread
from leap.util.files import check_and_fix_urw_only, get_mtime
from leap.util.request_helpers import get_content

logger = logging.getLogger(__name__)


class EIPBootstrapper(QtCore.QObject):
    """
    Sets up EIP for a provider a series of checks and emits signals
    after they are passed.
    If a check fails, the subsequent checks are not executed
    """

    PASSED_KEY = "passed"
    ERROR_KEY = "error"

    IDLE_SLEEP_INTERVAL = 100

    # All dicts returned are of the form
    # {"passed": bool, "error": str}
    download_config = QtCore.Signal(dict)
    download_client_certificate = QtCore.Signal(dict)

    def __init__(self):
        QtCore.QObject.__init__(self)

        # **************************************************** #
        # Dependency injection helpers, override this for more
        # granular testing
        self._fetcher = requests
        # **************************************************** #

        self._session = self._fetcher.session()
        self._provider_config = None
        self._eip_config = None
        self._download_if_needed = False

    def _download_config(self):
        """
        Downloads the EIP config for the given provider

        @return: True if the checks passed, False otherwise
        @rtype: bool
        """

        leap_assert(self._provider_config,
                    "We need a provider configuration!")

        logger.debug("Downloading EIP config for %s" %
                     (self._provider_config.get_domain(),))

        download_config_data = {
            self.PASSED_KEY: False,
            self.ERROR_KEY: ""
        }

        self._eip_config = EIPConfig()

        try:
            headers = {}
            mtime = get_mtime(os.path.join(self._eip_config
                                           .get_path_prefix(),
                                           "leap",
                                           "providers",
                                           self._provider_config.get_domain(),
                                           "eip-service.json"))

            if self._download_if_needed and mtime:
                headers['if-modified-since'] = mtime

            res = self._session.get("%s/%s/%s/%s" %
                                    (self._provider_config.get_api_uri(),
                                     self._provider_config.get_api_version(),
                                     "config",
                                     "eip-service.json"),
                                    verify=self._provider_config
                                    .get_ca_cert_path(),
                                    headers=headers)
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

            download_config_data[self.PASSED_KEY] = True
        except Exception as e:
            download_config_data[self.ERROR_KEY] = "%s" % (e,)

        logger.debug("Emitting download_config %s" % (download_config_data,))
        self.download_config.emit(download_config_data)

        return download_config_data[self.PASSED_KEY]

    def _download_client_certificates(self):
        """
        Downloads the EIP client certificate for the given provider

        @return: True if the checks passed, False otherwise
        @rtype: bool
        """
        leap_assert(self._provider_config, "We need a provider configuration!")
        leap_assert(self._eip_config, "We need an eip configuration!")

        logger.debug("Downloading EIP client certificate for %s" %
                     (self._provider_config.get_domain(),))

        download_cert = {
            self.PASSED_KEY: False,
            self.ERROR_KEY: ""
        }

        client_cert_path = self._eip_config.\
            get_client_cert_path(self._provider_config,
                                 about_to_download=True)

        if self._download_if_needed and \
                os.path.exists(client_cert_path):
            try:
                check_and_fix_urw_only(client_cert_path)
                download_cert[self.PASSED_KEY] = True
            except Exception as e:
                download_cert[self.PASSED_KEY] = False
                download_cert[self.ERROR_KEY] = "%s" % (e,)
            self.download_client_certificate.emit(download_cert)
            return download_cert[self.PASSED_KEY]

        try:
            srp_auth = SRPAuth(self._provider_config)
            session_id = srp_auth.get_session_id()
            cookies = None
            if session_id:
                cookies = {"_session_id": session_id}
            res = self._session.get("%s/%s/%s/" %
                                    (self._provider_config.get_api_uri(),
                                     self._provider_config.get_api_version(),
                                     "cert"),
                                    verify=self._provider_config
                                    .get_ca_cert_path(),
                                    cookies=cookies)
            res.raise_for_status()

            client_cert = res.content

            # TODO: check certificate validity

            try:
                os.makedirs(os.path.dirname(client_cert_path))
            except OSError as e:
                if e.errno == errno.EEXIST and \
                        os.path.isdir(os.path.dirname(client_cert_path)):
                    pass
                else:
                    raise

            with open(client_cert_path, "w") as f:
                f.write(client_cert)

            check_and_fix_urw_only(client_cert_path)

            download_cert[self.PASSED_KEY] = True
        except Exception as e:
            download_cert[self.ERROR_KEY] = "%s" % (e,)

        logger.debug("Emitting download_client_certificates %s" %
                     (download_cert,))
        self.download_client_certificate.emit(download_cert)

        return download_cert[self.PASSED_KEY]

    def run_eip_setup_checks(self, checker,
                             provider_config,
                             download_if_needed=False):
        """
        Starts the checks needed for a new eip setup

        @param provider_config: Provider configuration
        @type provider_config: ProviderConfig
        """
        leap_assert(provider_config, "We need a provider config!")
        leap_assert_type(provider_config, ProviderConfig)

        self._provider_config = provider_config
        self._download_if_needed = download_if_needed

        checker.add_checks([
            self._download_config,
            self._download_client_certificates
        ])


if __name__ == "__main__":
    import sys
    from functools import partial
    app = QtGui.QApplication(sys.argv)

    import signal

    def sigint_handler(*args, **kwargs):
        logger.debug('SIGINT catched. shutting down...')
        checker = args[0]
        checker.set_should_quit()
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

    eip_checks = EIPBootstrapper()
    checker = CheckerThread()

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

    checker.start()

    provider_config = ProviderConfig()
    if provider_config.load(os.path.join("leap",
                                         "providers",
                                         "bitmask.net",
                                         "provider.json")):
        eip_checks.run_eip_setup_checks(checker, provider_config)

    sys.exit(app.exec_())
