# -*- coding: utf-8 -*-
# srpregister.py
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

import binascii
import logging

import requests
import srp

from PySide import QtCore
from urlparse import urlparse

from leap.config.providerconfig import ProviderConfig
from leap.crypto.constants import SIGNUP_TIMEOUT
from leap.common.check import leap_assert, leap_assert_type

logger = logging.getLogger(__name__)


class SRPRegister(QtCore.QObject):
    """
    Registers a user to a specific provider using SRP
    """

    USER_LOGIN_KEY = 'user[login]'
    USER_VERIFIER_KEY = 'user[password_verifier]'
    USER_SALT_KEY = 'user[password_salt]'

    registration_finished = QtCore.Signal(bool, object)

    def __init__(self,
                 provider_config=None,
                 register_path="users"):
        """
        Constructor

        @param provider_config: provider configuration instance,
        properly loaded
        @type privider_config: ProviderConfig
        @param register_path: webapp path for registering users
        @type register_path; str
        """
        QtCore.QObject.__init__(self)
        leap_assert(provider_config, "Please provide a provider")
        leap_assert_type(provider_config, ProviderConfig)

        self._provider_config = provider_config

        # **************************************************** #
        # Dependency injection helpers, override this for more
        # granular testing
        self._fetcher = requests
        self._srp = srp
        self._hashfun = self._srp.SHA256
        self._ng = self._srp.NG_1024
        # **************************************************** #

        parsed_url = urlparse(provider_config.get_api_uri())
        self._provider = parsed_url.hostname
        self._port = parsed_url.port
        if self._port is None:
            self._port = "443"

        self._register_path = register_path

        self._session = self._fetcher.session()

    def _get_registration_uri(self):
        """
        Returns the URI where the register request should be made for
        the provider

        @rtype: str
        """

        uri = "https://%s:%s/%s/%s" % (
            self._provider,
            self._port,
            self._provider_config.get_api_version(),
            self._register_path)

        return uri

    def register_user(self, username, password):
        """
        Registers a user with the validator based on the password provider

        @param username: username to register
        @type username: str
        @param password: password for this username
        @type password: str

        @rtype: tuple
        @rparam: (ok, request)
        """
        salt, verifier = self._srp.create_salted_verification_key(
            username,
            password,
            self._hashfun,
            self._ng)

        user_data = {
            self.USER_LOGIN_KEY: username,
            self.USER_VERIFIER_KEY: binascii.hexlify(verifier),
            self.USER_SALT_KEY: binascii.hexlify(salt)
        }

        uri = self._get_registration_uri()

        logger.debug('Post to uri: %s' % uri)
        logger.debug("Will try to register user = %s" % (username,))
        logger.debug("user_data => %r" % (user_data,))

        ok = None
        try:
            req = self._session.post(uri,
                                     data=user_data,
                                     timeout=SIGNUP_TIMEOUT,
                                     verify=self._provider_config.
                                     get_ca_cert_path())

        except requests.exceptions.SSLError as exc:
            logger.error("SSLError: %s" % exc.message)
            req = None
            ok = False
        else:
            ok = req.ok
        self.registration_finished.emit(ok, req)
        return ok


if __name__ == "__main__":
    logger = logging.getLogger(name='leap')
    logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s '
        '- %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)

    provider = ProviderConfig()

    if provider.load("leap/providers/bitmask.net/provider.json"):
        register = SRPRegister(provider_config=provider)
        print "Registering user..."
        print register.register_user("test1", "sarasaaaa")
        print register.register_user("test2", "sarasaaaa")
