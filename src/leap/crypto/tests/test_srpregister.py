# -*- coding: utf-8 -*-
# test_srpregister.py
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
Tests for:
    * leap/crypto/srpregister.py
    * leap/crypto/srpauth.py
"""
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os
import sys

from mock import MagicMock
from nose.twistedtools import reactor, deferred
from twisted.python import log
from twisted.internet import threads

from leap.common.testing.https_server import where
from leap.config.providerconfig import ProviderConfig
from leap.crypto import srpregister, srpauth
from leap.crypto.tests import fake_provider

log.startLogging(sys.stdout)


def _get_capath():
    return where("cacert.pem")

_here = os.path.split(__file__)[0]


class ImproperlyConfiguredError(Exception):
    """
    Raised if the test provider is missing configuration
    """


class SRPTestCase(unittest.TestCase):
    """
    Tests for the SRP Register and Auth classes
    """
    __name__ = "SRPRegister and SRPAuth tests"

    @classmethod
    def setUpClass(cls):
        """
        Sets up this TestCase with a simple and faked provider instance:

        * runs a threaded reactor
        * loads a mocked ProviderConfig that points to the certs in the
          leap.common.testing module.
        """
        factory = fake_provider.get_provider_factory()
        http = reactor.listenTCP(8001, factory)
        https = reactor.listenSSL(
            0, factory,
            fake_provider.OpenSSLServerContextFactory())
        get_port = lambda p: p.getHost().port
        cls.http_port = get_port(http)
        cls.https_port = get_port(https)

        provider = ProviderConfig()
        provider.get_ca_cert_path = MagicMock()
        provider.get_ca_cert_path.return_value = _get_capath()

        provider.get_api_uri = MagicMock()
        provider.get_api_uri.return_value = cls._get_https_uri()

        loaded = provider.load(path=os.path.join(
            _here, "test_provider.json"))
        if not loaded:
            raise ImproperlyConfiguredError(
                "Could not load test provider config")
        cls.register = srpregister.SRPRegister(provider_config=provider)

        cls.auth = srpauth.SRPAuth(provider)

    # helper methods

    @classmethod
    def _get_https_uri(cls):
        """
        Returns a https uri with the right https port initialized
        """
        return "https://localhost:%s" % (cls.https_port,)

    # Register tests

    def test_none_port(self):
        provider = ProviderConfig()
        provider.get_api_uri = MagicMock()
        provider.get_api_uri.return_value = "http://localhost/"
        loaded = provider.load(path=os.path.join(
            _here, "test_provider.json"))
        if not loaded:
            raise ImproperlyConfiguredError(
                "Could not load test provider config")

        register = srpregister.SRPRegister(provider_config=provider)
        self.assertEquals(register._port, "443")

    @deferred()
    def test_wrong_cert(self):
        provider = ProviderConfig()
        loaded = provider.load(path=os.path.join(
            _here, "test_provider.json"))
        provider.get_ca_cert_path = MagicMock()
        provider.get_ca_cert_path.return_value = os.path.join(
            _here,
            "wrongcacert.pem")
        provider.get_api_uri = MagicMock()
        provider.get_api_uri.return_value = self._get_https_uri()
        if not loaded:
            raise ImproperlyConfiguredError(
                "Could not load test provider config")

        register = srpregister.SRPRegister(provider_config=provider)
        d = threads.deferToThread(register.register_user, "foouser_firsttime",
                                  "barpass")
        d.addCallback(self.assertFalse)
        return d

    @deferred()
    def test_register_user(self):
        """
        Checks if the registration of an unused name works as expected when
        it is the first time that we attempt to register that user, as well as
        when we request a user that is taken.
        """
        # pristine registration
        d = threads.deferToThread(self.register.register_user,
                                  "foouser_firsttime",
                                  "barpass")
        d.addCallback(self.assertTrue)
        return d

    @deferred()
    def test_second_register_user(self):
        # second registration attempt with the same user should return errors
        d = threads.deferToThread(self.register.register_user,
                                  "foouser_second",
                                  "barpass")
        d.addCallback(self.assertTrue)

        # FIXME currently we are catching this in an upper layer,
        # we could bring the error validation to the SRPRegister class
        def register_wrapper(_):
            return threads.deferToThread(self.register.register_user,
                                         "foouser_second",
                                         "barpass")
        d.addCallback(register_wrapper)
        d.addCallback(self.assertFalse)
        return d

    @deferred()
    def test_correct_http_uri(self):
        """
        Checks that registration autocorrect http uris to https ones.
        """
        HTTP_URI = "http://localhost:%s" % (self.https_port, )
        HTTPS_URI = "https://localhost:%s/1/users" % (self.https_port, )
        provider = ProviderConfig()
        provider.get_ca_cert_path = MagicMock()
        provider.get_ca_cert_path.return_value = _get_capath()
        provider.get_api_uri = MagicMock()

        # we introduce a http uri in the config file...
        provider.get_api_uri.return_value = HTTP_URI
        loaded = provider.load(path=os.path.join(
            _here, "test_provider.json"))
        if not loaded:
            raise ImproperlyConfiguredError(
                "Could not load test provider config")

        register = srpregister.SRPRegister(provider_config=provider)

        # ... and we check that we're correctly taking the HTTPS protocol
        # instead
        reg_uri = register._get_registration_uri()
        self.assertEquals(reg_uri, HTTPS_URI)
        register._get_registration_uri = MagicMock(return_value=HTTPS_URI)
        d = threads.deferToThread(register.register_user, "test_failhttp",
                                  "barpass")
        d.addCallback(self.assertTrue)

        return d
