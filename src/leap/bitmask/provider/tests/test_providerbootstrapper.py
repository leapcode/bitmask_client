# -*- coding: utf-8 -*-
# test_providerbootstrapper.py
# Copyright (C) 2013 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
Tests for the Provider Boostrapper checks

These will be whitebox tests since we want to make sure the private
implementation is checking what we expect.
"""
import os
import mock
import socket
import stat
import tempfile
import time
import requests
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from nose.twistedtools import deferred, reactor
from twisted.internet import threads
from requests.models import Response

from leap.bitmask.config.providerconfig import ProviderConfig
from leap.bitmask.crypto.tests import fake_provider
from leap.bitmask.provider.providerbootstrapper import ProviderBootstrapper
from leap.bitmask.provider.providerbootstrapper import UnsupportedProviderAPI
from leap.bitmask.provider.providerbootstrapper import WrongFingerprint
from leap.bitmask.provider.supportedapis import SupportedAPIs
from leap.common.files import mkdir_p
from leap.common.testing.https_server import where
from leap.common.testing.basetest import BaseLeapTest


class ProviderBootstrapperTest(BaseLeapTest):
    def setUp(self):
        self.pb = ProviderBootstrapper()

    def tearDown(self):
        pass

    def test_name_resolution_check(self):
        # Something highly likely to success
        self.pb._domain = "google.com"
        self.pb._check_name_resolution()
        # Something highly likely to fail
        self.pb._domain = "uquhqweuihowquie.abc.def"

        # In python 2.7.4 raises socket.error
        # In python 2.7.5 raises socket.gaierror
        with self.assertRaises((socket.gaierror, socket.error)):
            self.pb._check_name_resolution()

    @deferred()
    def test_run_provider_select_checks(self):
        self.pb._check_name_resolution = mock.MagicMock()
        self.pb._check_https = mock.MagicMock()
        self.pb._download_provider_info = mock.MagicMock()

        d = self.pb.run_provider_select_checks("somedomain")

        def check(*args):
            self.pb._check_name_resolution.assert_called_once_with()
            self.pb._check_https.assert_called_once_with(None)
            self.pb._download_provider_info.assert_called_once_with(None)
        d.addCallback(check)
        return d

    @deferred()
    def test_run_provider_setup_checks(self):
        self.pb._download_ca_cert = mock.MagicMock()
        self.pb._check_ca_fingerprint = mock.MagicMock()
        self.pb._check_api_certificate = mock.MagicMock()

        d = self.pb.run_provider_setup_checks(ProviderConfig())

        def check(*args):
            self.pb._download_ca_cert.assert_called_once_with()
            self.pb._check_ca_fingerprint.assert_called_once_with(None)
            self.pb._check_api_certificate.assert_called_once_with(None)
        d.addCallback(check)
        return d

    def test_should_proceed_cert(self):
        self.pb._provider_config = mock.Mock()
        self.pb._provider_config.get_ca_cert_path = mock.MagicMock(
            return_value=where("cacert.pem"))

        self.pb._download_if_needed = False
        self.assertTrue(self.pb._should_proceed_cert())

        self.pb._download_if_needed = True
        self.assertFalse(self.pb._should_proceed_cert())

        self.pb._provider_config.get_ca_cert_path = mock.MagicMock(
            return_value=where("somefilethatdoesntexist.pem"))
        self.assertTrue(self.pb._should_proceed_cert())

    def _check_download_ca_cert(self, should_proceed):
        """
        Helper to check different paths easily for the download ca
        cert check

        :param should_proceed: sets the _should_proceed_cert in the
                               provider bootstrapper being tested
        :type should_proceed: bool

        :returns: The contents of the certificate, the expected
                  content depending on should_proceed, and the mode of
                  the file to be checked by the caller
        :rtype: tuple of str, str, int
        """
        old_content = "NOT THE NEW CERT"
        new_content = "NEW CERT"
        new_cert_path = os.path.join(tempfile.mkdtemp(),
                                     "mynewcert.pem")

        with open(new_cert_path, "w") as c:
            c.write(old_content)

        self.pb._provider_config = mock.Mock()
        self.pb._provider_config.get_ca_cert_path = mock.MagicMock(
            return_value=new_cert_path)
        self.pb._domain = "somedomain"

        self.pb._should_proceed_cert = mock.MagicMock(
            return_value=should_proceed)

        read = None
        content_to_check = None
        mode = None

        with mock.patch('requests.models.Response.content',
                        new_callable=mock.PropertyMock) as \
                content:
            content.return_value = new_content
            response_obj = Response()
            response_obj.raise_for_status = mock.MagicMock()

            self.pb._session.get = mock.MagicMock(return_value=response_obj)
            self.pb._download_ca_cert()
            with open(new_cert_path, "r") as nc:
                read = nc.read()
                if should_proceed:
                    content_to_check = new_content
                else:
                    content_to_check = old_content
            mode = stat.S_IMODE(os.stat(new_cert_path).st_mode)

        os.unlink(new_cert_path)
        return read, content_to_check, mode

    def test_download_ca_cert_no_saving(self):
        read, expected_read, mode = self._check_download_ca_cert(False)
        self.assertEqual(read, expected_read)
        self.assertEqual(mode, int("600", 8))

    def test_download_ca_cert_saving(self):
        read, expected_read, mode = self._check_download_ca_cert(True)
        self.assertEqual(read, expected_read)
        self.assertEqual(mode, int("600", 8))

    def test_check_ca_fingerprint_skips(self):
        self.pb._provider_config = mock.Mock()
        self.pb._provider_config.get_ca_cert_fingerprint = mock.MagicMock(
            return_value="")
        self.pb._domain = "somedomain"

        self.pb._should_proceed_cert = mock.MagicMock(return_value=False)

        self.pb._check_ca_fingerprint()
        self.assertFalse(self.pb._provider_config.
                         get_ca_cert_fingerprint.called)

    def test_check_ca_cert_fingerprint_raises_bad_format(self):
        self.pb._provider_config = mock.Mock()
        self.pb._provider_config.get_ca_cert_fingerprint = mock.MagicMock(
            return_value="wrongfprformat!!")
        self.pb._domain = "somedomain"

        self.pb._should_proceed_cert = mock.MagicMock(return_value=True)

        with self.assertRaises(WrongFingerprint):
            self.pb._check_ca_fingerprint()

    # This two hashes different in the last byte, but that's good enough
    # for the tests
    KNOWN_BAD_HASH = "SHA256: 0f17c033115f6b76ff67871872303ff65034efe" \
                     "7dd1b910062ca323eb4da5c7f"
    KNOWN_GOOD_HASH = "SHA256: 0f17c033115f6b76ff67871872303ff65034ef" \
                      "e7dd1b910062ca323eb4da5c7e"
    KNOWN_GOOD_CERT = """
-----BEGIN CERTIFICATE-----
MIIFbzCCA1egAwIBAgIBATANBgkqhkiG9w0BAQ0FADBKMRgwFgYDVQQDDA9CaXRt
YXNrIFJvb3QgQ0ExEDAOBgNVBAoMB0JpdG1hc2sxHDAaBgNVBAsME2h0dHBzOi8v
Yml0bWFzay5uZXQwHhcNMTIxMTA2MDAwMDAwWhcNMjIxMTA2MDAwMDAwWjBKMRgw
FgYDVQQDDA9CaXRtYXNrIFJvb3QgQ0ExEDAOBgNVBAoMB0JpdG1hc2sxHDAaBgNV
BAsME2h0dHBzOi8vYml0bWFzay5uZXQwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAw
ggIKAoICAQC1eV4YvayaU+maJbWrD4OHo3d7S1BtDlcvkIRS1Fw3iYDjsyDkZxai
dHp4EUasfNQ+EVtXUvtk6170EmLco6Elg8SJBQ27trE6nielPRPCfX3fQzETRfvB
7tNvGw4Jn2YKiYoMD79kkjgyZjkJ2r/bEHUSevmR09BRp86syHZerdNGpXYhcQ84
CA1+V+603GFIHnrP+uQDdssW93rgDNYu+exT+Wj6STfnUkugyjmPRPjL7wh0tzy+
znCeLl4xiV3g9sjPnc7r2EQKd5uaTe3j71sDPF92KRk0SSUndREz+B1+Dbe/RGk4
MEqGFuOzrtsgEhPIX0hplhb0Tgz/rtug+yTT7oJjBa3u20AAOQ38/M99EfdeJvc4
lPFF1XBBLh6X9UKF72an2NuANiX6XPySnJgZ7nZ09RiYZqVwu/qt3DfvLfhboq+0
bQvLUPXrVDr70onv5UDjpmEA/cLmaIqqrduuTkFZOym65/PfAPvpGnt7crQj/Ibl
DEDYZQmP7AS+6zBjoOzNjUGE5r40zWAR1RSi7zliXTu+yfsjXUIhUAWmYR6J3KxB
lfsiHBQ+8dn9kC3YrUexWoOqBiqJOAJzZh5Y1tqgzfh+2nmHSB2dsQRs7rDRRlyy
YMbkpzL9ZsOUO2eTP1mmar6YjCN+rggYjRrX71K2SpBG6b1zZxOG+wIDAQABo2Aw
XjAdBgNVHQ4EFgQUuYGDLL2sswnYpHHvProt1JU+D48wDgYDVR0PAQH/BAQDAgIE
MAwGA1UdEwQFMAMBAf8wHwYDVR0jBBgwFoAUuYGDLL2sswnYpHHvProt1JU+D48w
DQYJKoZIhvcNAQENBQADggIBADeG67vaFcbITGpi51264kHPYPEWaXUa5XYbtmBl
cXYyB6hY5hv/YNuVGJ1gWsDmdeXEyj0j2icGQjYdHRfwhrbEri+h1EZOm1cSBDuY
k/P5+ctHyOXx8IE79DBsZ6IL61UKIaKhqZBfLGYcWu17DVV6+LT+AKtHhOrv3TSj
RnAcKnCbKqXLhUPXpK0eTjPYS2zQGQGIhIy9sQXVXJJJsGrPgMxna1Xw2JikBOCG
htD/JKwt6xBmNwktH0GI/LVtVgSp82Clbn9C4eZN9E5YbVYjLkIEDhpByeC71QhX
EIQ0ZR56bFuJA/CwValBqV/G9gscTPQqd+iETp8yrFpAVHOW+YzSFbxjTEkBte1J
aF0vmbqdMAWLk+LEFPQRptZh0B88igtx6tV5oVd+p5IVRM49poLhuPNJGPvMj99l
mlZ4+AeRUnbOOeAEuvpLJbel4rhwFzmUiGoeTVoPZyMevWcVFq6BMkS+jRR2w0jK
G6b0v5XDHlcFYPOgUrtsOBFJVwbutLvxdk6q37kIFnWCd8L3kmES5q4wjyFK47Co
Ja8zlx64jmMZPg/t3wWqkZgXZ14qnbyG5/lGsj5CwVtfDljrhN0oCWK1FZaUmW3d
69db12/g4f6phldhxiWuGC/W6fCW5kre7nmhshcltqAJJuU47iX+DarBFiIj816e
yV8e
-----END CERTIFICATE-----
"""

    def _prepare_provider_config_with(self, cert_path, cert_hash):
        """
        Mocks the provider config to give the cert_path and cert_hash
        specified

        :param cert_path: path for the certificate
        :type cert_path: str
        :param cert_hash: hash for the certificate as it would appear
                          in the provider config json
        :type cert_hash: str
        """
        self.pb._provider_config = mock.Mock()
        self.pb._provider_config.get_ca_cert_fingerprint = mock.MagicMock(
            return_value=cert_hash)
        self.pb._provider_config.get_ca_cert_path = mock.MagicMock(
            return_value=cert_path)
        self.pb._domain = "somedomain"

    def test_check_ca_fingerprint_checksout(self):
        cert_path = os.path.join(tempfile.mkdtemp(),
                                 "mynewcert.pem")

        with open(cert_path, "w") as c:
            c.write(self.KNOWN_GOOD_CERT)

        self._prepare_provider_config_with(cert_path, self.KNOWN_GOOD_HASH)

        self.pb._should_proceed_cert = mock.MagicMock(return_value=True)

        self.pb._check_ca_fingerprint()

        os.unlink(cert_path)

    def test_check_ca_fingerprint_fails(self):
        cert_path = os.path.join(tempfile.mkdtemp(),
                                 "mynewcert.pem")

        with open(cert_path, "w") as c:
            c.write(self.KNOWN_GOOD_CERT)

        self._prepare_provider_config_with(cert_path, self.KNOWN_BAD_HASH)

        self.pb._should_proceed_cert = mock.MagicMock(return_value=True)

        with self.assertRaises(WrongFingerprint):
            self.pb._check_ca_fingerprint()

        os.unlink(cert_path)


###############################################################################
# Tests with a fake provider                                                  #
###############################################################################

class ProviderBootstrapperActiveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        factory = fake_provider.get_provider_factory()
        http = reactor.listenTCP(8002, factory)
        https = reactor.listenSSL(
            0, factory,
            fake_provider.OpenSSLServerContextFactory())
        get_port = lambda p: p.getHost().port
        cls.http_port = get_port(http)
        cls.https_port = get_port(https)

    def setUp(self):
        self.pb = ProviderBootstrapper()

        # At certain points we are going to be replacing these methods
        # directly in ProviderConfig to be able to catch calls from
        # new ProviderConfig objects inside the methods tested. We
        # need to save the old implementation and restore it in
        # tearDown so we are sure everything is as expected for each
        # test. If we do it inside each specific test, a failure in
        # the test will leave the implementation with the mock.
        self.old_gpp = ProviderConfig.get_path_prefix
        self.old_load = ProviderConfig.load
        self.old_save = ProviderConfig.save
        self.old_api_version = ProviderConfig.get_api_version

    def tearDown(self):
        ProviderConfig.get_path_prefix = self.old_gpp
        ProviderConfig.load = self.old_load
        ProviderConfig.save = self.old_save
        ProviderConfig.get_api_version = self.old_api_version

    def test_check_https_succeeds(self):
        # XXX: Need a proper CA signed cert to test this
        pass

    @deferred()
    def test_check_https_fails(self):
        self.pb._domain = "localhost:%s" % (self.https_port,)

        def check(*args):
            with self.assertRaises(requests.exceptions.SSLError):
                self.pb._check_https()
        return threads.deferToThread(check)

    @deferred()
    def test_second_check_https_fails(self):
        self.pb._domain = "localhost:1234"

        def check(*args):
            with self.assertRaises(Exception):
                self.pb._check_https()
        return threads.deferToThread(check)

    @deferred()
    def test_check_https_succeeds_if_danger(self):
        self.pb._domain = "localhost:%s" % (self.https_port,)
        self.pb._bypass_checks = True

        def check(*args):
            self.pb._check_https()

        return threads.deferToThread(check)

    def _setup_provider_config_with(self, api, path_prefix):
        """
        Sets up the ProviderConfig with mocks for the path prefix, the
        api returned and load/save methods.
        It modifies ProviderConfig directly instead of an object
        because the object used is created in the method itself and we
        cannot control that.

        :param api: API to return
        :type api: str
        :param path_prefix: path prefix to be used when calculating
                            paths
        :type path_prefix: str
        """
        ProviderConfig.get_path_prefix = mock.MagicMock(
            return_value=path_prefix)
        ProviderConfig.get_api_version = mock.MagicMock(
            return_value=api)
        ProviderConfig.load = mock.MagicMock()
        ProviderConfig.save = mock.MagicMock()

    def _setup_providerbootstrapper(self, ifneeded):
        """
        Sets the provider bootstrapper's domain to
        localhost:https_port, sets it to bypass https checks and sets
        the download if needed based on the ifneeded value.

        :param ifneeded: Value for _download_if_needed
        :type ifneeded: bool
        """
        self.pb._domain = "localhost:%s" % (self.https_port,)
        self.pb._bypass_checks = True
        self.pb._download_if_needed = ifneeded

    def _produce_dummy_provider_json(self):
        """
        Creates a dummy provider json on disk in order to test
        behaviour around it (download if newer online, etc)

        :returns: the provider.json path used
        :rtype: str
        """
        provider_dir = os.path.join(ProviderConfig()
                                    .get_path_prefix(),
                                    "leap",
                                    "providers",
                                    self.pb._domain)
        mkdir_p(provider_dir)
        provider_path = os.path.join(provider_dir,
                                     "provider.json")

        with open(provider_path, "w") as p:
            p.write("A")
        return provider_path

    def test_download_provider_info_new_provider(self):
        self._setup_provider_config_with("1", tempfile.mkdtemp())
        self._setup_providerbootstrapper(True)

        self.pb._download_provider_info()
        self.assertTrue(ProviderConfig.save.called)

    @mock.patch(
        'leap.bitmask.config.providerconfig.ProviderConfig.get_ca_cert_path',
        lambda x: where('cacert.pem'))
    def test_download_provider_info_not_modified(self):
        self._setup_provider_config_with("1", tempfile.mkdtemp())
        self._setup_providerbootstrapper(True)
        provider_path = self._produce_dummy_provider_json()

        # set mtime to something really new
        os.utime(provider_path, (-1, time.time()))

        with mock.patch.object(
                ProviderConfig, 'get_api_uri',
                return_value="https://localhost:%s" % (self.https_port,)):
            self.pb._download_provider_info()
        # we check that it doesn't save the provider
        # config, because it's new enough
        self.assertFalse(ProviderConfig.save.called)

    @mock.patch(
        'leap.bitmask.config.providerconfig.ProviderConfig.get_domain',
        lambda x: where('testdomain.com'))
    def test_download_provider_info_not_modified_and_no_cacert(self):
        self._setup_provider_config_with("1", tempfile.mkdtemp())
        self._setup_providerbootstrapper(True)
        provider_path = self._produce_dummy_provider_json()

        # set mtime to something really new
        os.utime(provider_path, (-1, time.time()))

        with mock.patch.object(
                ProviderConfig, 'get_api_uri',
                return_value="https://localhost:%s" % (self.https_port,)):
            self.pb._download_provider_info()
        # we check that it doesn't save the provider
        # config, because it's new enough
        self.assertFalse(ProviderConfig.save.called)

    @mock.patch(
        'leap.bitmask.config.providerconfig.ProviderConfig.get_ca_cert_path',
        lambda x: where('cacert.pem'))
    def test_download_provider_info_modified(self):
        self._setup_provider_config_with("1", tempfile.mkdtemp())
        self._setup_providerbootstrapper(True)
        provider_path = self._produce_dummy_provider_json()

        # set mtime to something really old
        os.utime(provider_path, (-1, 100))

        with mock.patch.object(
                ProviderConfig, 'get_api_uri',
                return_value="https://localhost:%s" % (self.https_port,)):
            self.pb._download_provider_info()
        self.assertTrue(ProviderConfig.load.called)
        self.assertTrue(ProviderConfig.save.called)

    @mock.patch(
        'leap.bitmask.config.providerconfig.ProviderConfig.get_ca_cert_path',
        lambda x: where('cacert.pem'))
    def test_download_provider_info_unsupported_api_raises(self):
        self._setup_provider_config_with("9999999", tempfile.mkdtemp())
        self._setup_providerbootstrapper(False)
        self._produce_dummy_provider_json()

        with mock.patch.object(
                ProviderConfig, 'get_api_uri',
                return_value="https://localhost:%s" % (self.https_port,)):
            with self.assertRaises(UnsupportedProviderAPI):
                self.pb._download_provider_info()

    @mock.patch(
        'leap.bitmask.config.providerconfig.ProviderConfig.get_ca_cert_path',
        lambda x: where('cacert.pem'))
    def test_download_provider_info_unsupported_api(self):
        self._setup_provider_config_with(SupportedAPIs.SUPPORTED_APIS[0],
                                         tempfile.mkdtemp())
        self._setup_providerbootstrapper(False)
        self._produce_dummy_provider_json()

        with mock.patch.object(
                ProviderConfig, 'get_api_uri',
                return_value="https://localhost:%s" % (self.https_port,)):
            self.pb._download_provider_info()

    @mock.patch(
        'leap.bitmask.config.providerconfig.ProviderConfig.get_api_uri',
        lambda x: 'api.uri')
    @mock.patch(
        'leap.bitmask.config.providerconfig.ProviderConfig.get_ca_cert_path',
        lambda x: '/cert/path')
    def test_check_api_certificate_skips(self):
        self.pb._provider_config = ProviderConfig()
        self.pb._session.get = mock.MagicMock(return_value=Response())

        self.pb._should_proceed_cert = mock.MagicMock(return_value=False)
        self.pb._check_api_certificate()
        self.assertFalse(self.pb._session.get.called)

    @deferred()
    def test_check_api_certificate_fails(self):
        self.pb._provider_config = ProviderConfig()
        self.pb._provider_config.get_api_uri = mock.MagicMock(
            return_value="https://localhost:%s" % (self.https_port,))
        self.pb._provider_config.get_ca_cert_path = mock.MagicMock(
            return_value=os.path.join(
                os.path.split(__file__)[0],
                "wrongcert.pem"))
        self.pb._provider_config.get_api_version = mock.MagicMock(
            return_value="1")

        self.pb._should_proceed_cert = mock.MagicMock(return_value=True)

        def check(*args):
            with self.assertRaises(requests.exceptions.SSLError):
                self.pb._check_api_certificate()
        d = threads.deferToThread(check)
        return d

    @deferred()
    def test_check_api_certificate_succeeds(self):
        self.pb._provider_config = ProviderConfig()
        self.pb._provider_config.get_api_uri = mock.MagicMock(
            return_value="https://localhost:%s" % (self.https_port,))
        self.pb._provider_config.get_ca_cert_path = mock.MagicMock(
            return_value=where('cacert.pem'))
        self.pb._provider_config.get_api_version = mock.MagicMock(
            return_value="1")

        self.pb._should_proceed_cert = mock.MagicMock(return_value=True)

        def check(*args):
            self.pb._check_api_certificate()
        d = threads.deferToThread(check)
        return d
