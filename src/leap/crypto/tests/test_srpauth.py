# -*- coding: utf-8 -*-
# test_srpauth.py
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
Tests for leap/crypto/srpauth.py
"""
try:
    import unittest
except ImportError:
    import unittest
import os
import sys

from mock import MagicMock
from nose.twistedtools import reactor, threaded_reactor, stop_reactor
from twisted.python import log

from leap.common.testing.https_server import where
from leap.config.providerconfig import ProviderConfig
from leap.crypto import srpauth
from leap.crypto import srpregister
from leap.crypto.tests import fake_provider

log.startLogging(sys.stdout)


def _get_capath():
    return where("cacert.pem")

_here = os.path.split(__file__)[0]


class ImproperlyConfiguredError(Exception):
    """
    Raised if the test provider is missing configuration
    """


class SRPRegisterTestCase(unittest.TestCase):
    """
    Tests for the SRP Authentication class
    """
    __name__ = "SRPAuth tests"

    @classmethod
    def setUpClass(cls):
        """
        Sets up this TestCase with a simple and faked provider instance:

        * runs a threaded reactor
        * loads a mocked ProviderConfig that points to the certs in the
          leap.common.testing module.
        """
        factory = fake_provider.get_provider_factory()
        reactor.listenTCP(8000, factory)
        reactor.listenSSL(
            8443, factory,
            fake_provider.OpenSSLServerContextFactory())
        threaded_reactor()

        provider = ProviderConfig()
        provider.get_ca_cert_path = MagicMock()
        provider.get_ca_cert_path.return_value = _get_capath()
        loaded = provider.load(path=os.path.join(
            _here, "test_provider.json"))
        if not loaded:
            raise ImproperlyConfiguredError(
                "Could not load test provider config")
        cls.provider = provider
        cls.register = srpregister.SRPRegister(provider_config=provider)
        cls.auth = srpauth.SRPAuth(provider)
        cls._auth_instance = cls.auth.__dict__['_SRPAuth__instance']
        cls.authenticate = cls._auth_instance.authenticate
        cls.logout = cls._auth_instance.logout

    @classmethod
    def tearDownClass(cls):
        """
        Stops reactor when tearing down the class
        """
        stop_reactor()

    def test_auth(self):
        """
        Checks whether a pair of valid credentials is able to be authenticated.
        """
        TEST_USER = "register_test_auth"
        TEST_PASS = "pass"

        # pristine registration, should go well
        ok = self.register.register_user(TEST_USER, TEST_PASS)
        self.assertTrue(ok)

        self.authenticate(TEST_USER, TEST_PASS)
        with self.assertRaises(AssertionError):
            # AssertionError: already logged in
            # We probably could take this as its own exception
            self.authenticate(TEST_USER, TEST_PASS)

        self.logout()

        # cannot log out two times in a row (there's no session)
        with self.assertRaises(AssertionError):
            self.logout()

    def test_auth_with_bad_credentials(self):
        """
        Checks that auth does not succeed with bad credentials.
        """
        TEST_USER = "register_test_auth"
        TEST_PASS = "pass"

        # non-existent credentials, should fail
        with self.assertRaises(srpauth.SRPAuthenticationError):
            self.authenticate("baduser_1", "passwrong")

        # good user, bad password, should fail
        with self.assertRaises(srpauth.SRPAuthenticationError):
            self.authenticate(TEST_USER, "passwrong")

        # bad user, good password, should fail too :)
        with self.assertRaises(srpauth.SRPAuthenticationError):
            self.authenticate("myunclejoe", TEST_PASS)
