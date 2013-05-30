# -*- coding: utf-8 -*-
# soledadbootstrapper.py
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
Soledad bootstrapping
"""

import logging
import os

import requests

from PySide import QtCore
from mock import Mock

from leap.common.check import leap_assert, leap_assert_type
from leap.common.files import get_mtime
from leap.keymanager import KeyManager, openpgp
from leap.keymanager.errors import KeyNotFound
from leap.config.providerconfig import ProviderConfig
from leap.crypto.srpauth import SRPAuth
from leap.services.soledad.soledadconfig import SoledadConfig
from leap.util.request_helpers import get_content
from leap.soledad import Soledad

logger = logging.getLogger(__name__)


class SoledadBootstrapper(QtCore.QObject):
    """
    Soledad init procedure
    """

    PASSED_KEY = "passed"
    ERROR_KEY = "error"
    SOLEDAD_KEY = "soledad"
    KEYMANAGER_KEY = "keymanager"

    PUBKEY_KEY = "user[public_key]"

    IDLE_SLEEP_INTERVAL = 100

    # All dicts returned are of the form
    # {"passed": bool, "error": str}
    download_config = QtCore.Signal(dict)
    gen_key = QtCore.Signal(dict)

    def __init__(self):
        QtCore.QObject.__init__(self)

        # **************************************************** #
        # Dependency injection helpers, override this for more
        # granular testing
        self._fetcher = requests
        # **************************************************** #

        self._session = self._fetcher.session()
        self._provider_config = None
        self._soledad_config = None
        self._keymanager = None
        self._download_if_needed = False
        self._user = ""
        self._password = ""

    def _load_and_sync_soledad(self, srp_auth):
        """
        Once everthing is in the right place, we instantiate and sync
        Soledad

        :param srp_auth: SRPAuth object used
        :type srp_auth: SRPAuth
        """
        uuid = srp_auth.get_uid()

        prefix = os.path.join(self._soledad_config.get_path_prefix(),
                              "leap", "soledad")
        secrets_path = "%s/%s.secret" % (prefix, uuid)
        local_db_path = "%s/%s.db" % (prefix, uuid)

        # TODO: use the proper URL
        server_url = 'https://mole.dev.bitmask.net:2424/user-%s' % (uuid,)
        # server_url = self._soledad_config.get_hosts(...)

        cert_file = self._provider_config.get_ca_cert_path()

        self._soledad = Soledad(uuid,
                                self._password.encode("utf-8"),
                                secrets_path,
                                local_db_path,
                                server_url,
                                cert_file,
                                srp_auth.get_token())
        self._soledad.sync()

    def _download_config(self):
        """
        Downloads the Soledad config for the given provider

        :return: True if everything went as expected, False otherwise
        :rtype: bool
        """

        leap_assert(self._provider_config,
                    "We need a provider configuration!")

        logger.debug("Downloading Soledad config for %s" %
                     (self._provider_config.get_domain(),))

        download_config_data = {
            self.PASSED_KEY: False,
            self.ERROR_KEY: ""
        }

        self._soledad_config = SoledadConfig()

        try:
            headers = {}
            mtime = get_mtime(os.path.join(self._soledad_config
                                           .get_path_prefix(),
                                           "leap",
                                           "providers",
                                           self._provider_config.get_domain(),
                                           "soledad-service.json"))

            if self._download_if_needed and mtime:
                headers['if-modified-since'] = mtime

            # there is some confusion with this uri,
            config_uri = "%s/%s/config/soledad-service.json" % (
                self._provider_config.get_api_uri(),
                self._provider_config.get_api_version())
            logger.debug('Downloading soledad config from: %s' % config_uri)

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
                logger.debug("Soledad definition has not been modified")
            else:
                soledad_definition, mtime = get_content(res)

                self._soledad_config.load(data=soledad_definition, mtime=mtime)
                self._soledad_config.save(["leap",
                                           "providers",
                                           self._provider_config.get_domain(),
                                           "soledad-service.json"])

            self._load_and_sync_soledad(srp_auth)

            download_config_data[self.PASSED_KEY] = True
        except Exception as e:
            download_config_data[self.PASSED_KEY] = False
            download_config_data[self.ERROR_KEY] = "%s" % (e,)

        logger.debug("Emitting download_config %s" % (download_config_data,))
        self.download_config.emit(download_config_data)

        return download_config_data[self.PASSED_KEY]

    def _gen_key(self):
        """
        Generates the key pair if needed, uploads it to the webapp and
        nickserver

        :return: True if everything is done successfully, False
        otherwise
        :rtype: bool
        """
        leap_assert(self._provider_config,
                    "We need a provider configuration!")

        # XXX Sanitize this
        address = "%s@%s" % (self._user, self._provider_config.get_domain())

        logger.debug("Retrieving key for %s" % (address,))

        genkey_data = {
            self.PASSED_KEY: False,
            self.ERROR_KEY: "",
            self.SOLEDAD_KEY: None,
            self.KEYMANAGER_KEY: None
        }

        try:
            srp_auth = SRPAuth(self._provider_config)
            self._keymanager = KeyManager(
                address,
                "https://nickserver",  # TODO: nickserver url, none for now
                self._soledad,
                token=srp_auth.get_token())
            self._keymanager._fetcher.put = Mock()
            try:
                self._keymanager.get_key(address, openpgp.OpenPGPKey,
                                         private=True, fetch_remote=False)
            except KeyNotFound:
                logger.debug(
                    "Key not found. Generating key for %s" % (address,))
                self._keymanager.gen_key(openpgp.OpenPGPKey)

                logger.debug("Key generated successfully.")

            cookies = None
            session_id = srp_auth.get_session_id()
            if session_id:
                cookies = {"_session_id": session_id}

            key_uri = "%s/%s/users/%s.json" % (
                self._provider_config.get_api_uri(),
                self._provider_config.get_api_version(),
                srp_auth.get_uid())

            logger.debug("Uploading public key to %s" % (key_uri,))

            pubkey = self._keymanager.get_key(
                address, openpgp.OpenPGPKey,
                private=False, fetch_remote=False)
            key_data = {
                self.PUBKEY_KEY: pubkey.key_data,
            }

            # TODO: check if uploaded before uploading it
            key_result = self._session.put(key_uri,
                                           data=key_data,
                                           verify=self._provider_config
                                           .get_ca_cert_path(),
                                           cookies=cookies)
            key_result.raise_for_status()
            genkey_data[self.PASSED_KEY] = True
            genkey_data[self.SOLEDAD_KEY] = self._soledad
            genkey_data[self.KEYMANAGER_KEY] = self._keymanager
        except Exception as e:
            genkey_data[self.PASSED_KEY] = False
            genkey_data[self.ERROR_KEY] = "%s" % (e,)

        logger.debug("Emitting gen_key %s" % (genkey_data,))
        self.gen_key.emit(genkey_data)

        return genkey_data[self.PASSED_KEY]

    def run_soledad_setup_checks(self,
                                 checker,
                                 provider_config,
                                 user,
                                 password,
                                 download_if_needed=False):
        """
        Starts the checks needed for a new soledad setup

        :param provider_config: Provider configuration
        :type provider_config: ProviderConfig
        """
        leap_assert_type(provider_config, ProviderConfig)

        self._provider_config = provider_config
        self._download_if_needed = download_if_needed
        self._user = user
        self._password = password

        checker.add_checks([
            self._download_config,
            self._gen_key
        ])
