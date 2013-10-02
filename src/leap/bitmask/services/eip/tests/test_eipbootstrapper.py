# -*- coding: utf-8 -*-
# test_eipbootstrapper.py
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
Tests for the EIP Boostrapper checks

These will be whitebox tests since we want to make sure the private
implementation is checking what we expect.
"""

import os
import mock
import tempfile
import time
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from nose.twistedtools import deferred, reactor
from twisted.internet import threads
from requests.models import Response

from leap.bitmask.services.eip.eipbootstrapper import EIPBootstrapper
from leap.bitmask.services.eip.eipconfig import EIPConfig
from leap.bitmask.config.providerconfig import ProviderConfig
from leap.bitmask.crypto.tests import fake_provider
from leap.bitmask.crypto.srpauth import SRPAuth
from leap.bitmask import util
from leap.common.testing.basetest import BaseLeapTest
from leap.common.files import mkdir_p


class EIPBootstrapperActiveTest(BaseLeapTest):
    @classmethod
    def setUpClass(cls):
        BaseLeapTest.setUpClass()
        factory = fake_provider.get_provider_factory()
        http = reactor.listenTCP(0, factory)
        https = reactor.listenSSL(
            0, factory,
            fake_provider.OpenSSLServerContextFactory())
        get_port = lambda p: p.getHost().port
        cls.http_port = get_port(http)
        cls.https_port = get_port(https)

    def setUp(self):
        self.eb = EIPBootstrapper()
        self.old_pp = util.get_path_prefix
        self.old_save = EIPConfig.save
        self.old_load = EIPConfig.load
        self.old_si = SRPAuth.get_session_id

    def tearDown(self):
        util.get_path_prefix = self.old_pp
        EIPConfig.save = self.old_save
        EIPConfig.load = self.old_load
        SRPAuth.get_session_id = self.old_si

    def _download_config_test_template(self, ifneeded, new):
        """
        All download config tests have the same structure, so this is
        a parametrized test for that.

        :param ifneeded: sets _download_if_needed
        :type ifneeded: bool
        :param new: if True uses time.time() as mtime for the mocked
                    eip-service file, otherwise it uses 100 (a really
                    old mtime)
        :type new: float or int (will be coersed)
        """
        pc = ProviderConfig()
        pc.get_domain = mock.MagicMock(
            return_value="localhost:%s" % (self.https_port))
        self.eb._provider_config = pc

        pc.get_api_uri = mock.MagicMock(
            return_value="https://%s" % (pc.get_domain()))
        pc.get_api_version = mock.MagicMock(return_value="1")

        # This is to ignore https checking, since it's not the point
        # of this test
        pc.get_ca_cert_path = mock.MagicMock(return_value=False)

        path_prefix = tempfile.mkdtemp()
        util.get_path_prefix = mock.MagicMock(return_value=path_prefix)
        EIPConfig.save = mock.MagicMock()
        EIPConfig.load = mock.MagicMock()

        self.eb._download_if_needed = ifneeded

        provider_dir = os.path.join(util.get_path_prefix(),
                                    "leap",
                                    "providers",
                                    pc.get_domain())
        mkdir_p(provider_dir)
        eip_config_path = os.path.join(provider_dir,
                                       "eip-service.json")

        with open(eip_config_path, "w") as ec:
            ec.write("A")

        # set mtime to something really new
        if new:
            os.utime(eip_config_path, (-1, time.time()))
        else:
            os.utime(eip_config_path, (-1, 100))

    @deferred()
    def test_download_config_not_modified(self):
        self._download_config_test_template(True, True)

        d = threads.deferToThread(self.eb._download_config)

        def check(*args):
            self.assertFalse(self.eb._eip_config.save.called)
        d.addCallback(check)
        return d

    @deferred()
    def test_download_config_modified(self):
        self._download_config_test_template(True, False)

        d = threads.deferToThread(self.eb._download_config)

        def check(*args):
            self.assertTrue(self.eb._eip_config.save.called)
        d.addCallback(check)
        return d

    @deferred()
    def test_download_config_ignores_mtime(self):
        self._download_config_test_template(False, True)

        d = threads.deferToThread(self.eb._download_config)

        def check(*args):
            self.eb._eip_config.save.assert_called_once_with(
                ("leap",
                 "providers",
                 self.eb._provider_config.get_domain(),
                 "eip-service.json"))
        d.addCallback(check)
        return d

    def _download_certificate_test_template(self, ifneeded, createcert):
        """
        All download client certificate tests have the same structure,
        so this is a parametrized test for that.

        :param ifneeded: sets _download_if_needed
        :type ifneeded: bool
        :param createcert: if True it creates a dummy file to play the
                           part of a downloaded certificate
        :type createcert: bool

        :returns: the temp eip cert path and the dummy cert contents
        :rtype: tuple of str, str
        """
        pc = ProviderConfig()
        ec = EIPConfig()
        self.eb._provider_config = pc
        self.eb._eip_config = ec

        pc.get_domain = mock.MagicMock(
            return_value="localhost:%s" % (self.https_port))
        pc.get_api_uri = mock.MagicMock(
            return_value="https://%s" % (pc.get_domain()))
        pc.get_api_version = mock.MagicMock(return_value="1")
        pc.get_ca_cert_path = mock.MagicMock(return_value=False)

        path_prefix = tempfile.mkdtemp()
        util.get_path_prefix = mock.MagicMock(return_value=path_prefix)
        EIPConfig.save = mock.MagicMock()
        EIPConfig.load = mock.MagicMock()

        self.eb._download_if_needed = ifneeded

        provider_dir = os.path.join(util.get_path_prefix(),
                                    "leap",
                                    "providers",
                                    "somedomain")
        mkdir_p(provider_dir)
        eip_cert_path = os.path.join(provider_dir,
                                     "cert")

        ec.get_client_cert_path = mock.MagicMock(
            return_value=eip_cert_path)

        cert_content = "A"
        if createcert:
            with open(eip_cert_path, "w") as ec:
                ec.write(cert_content)

        return eip_cert_path, cert_content

    def test_download_client_certificate_not_modified(self):
        cert_path, old_cert_content = self._download_certificate_test_template(
            True, True)

        with mock.patch('leap.common.certs.should_redownload',
                        new_callable=mock.MagicMock,
                        return_value=False):
            self.eb._download_client_certificates()
            with open(cert_path, "r") as c:
                self.assertEqual(c.read(), old_cert_content)

    @deferred()
    def test_download_client_certificate_old_cert(self):
        cert_path, old_cert_content = self._download_certificate_test_template(
            True, True)

        def wrapper(*args):
            with mock.patch('leap.common.certs.should_redownload',
                            new_callable=mock.MagicMock,
                            return_value=True):
                with mock.patch('leap.common.certs.is_valid_pemfile',
                                new_callable=mock.MagicMock,
                                return_value=True):
                    self.eb._download_client_certificates()

        def check(*args):
            with open(cert_path, "r") as c:
                self.assertNotEqual(c.read(), old_cert_content)
        d = threads.deferToThread(wrapper)
        d.addCallback(check)

        return d

    @deferred()
    def test_download_client_certificate_no_cert(self):
        cert_path, _ = self._download_certificate_test_template(
            True, False)

        def wrapper(*args):
            with mock.patch('leap.common.certs.should_redownload',
                            new_callable=mock.MagicMock,
                            return_value=False):
                with mock.patch('leap.common.certs.is_valid_pemfile',
                                new_callable=mock.MagicMock,
                                return_value=True):
                    self.eb._download_client_certificates()

        def check(*args):
            self.assertTrue(os.path.exists(cert_path))
        d = threads.deferToThread(wrapper)
        d.addCallback(check)

        return d

    @deferred()
    def test_download_client_certificate_force_not_valid(self):
        cert_path, old_cert_content = self._download_certificate_test_template(
            True, True)

        def wrapper(*args):
            with mock.patch('leap.common.certs.should_redownload',
                            new_callable=mock.MagicMock,
                            return_value=True):
                with mock.patch('leap.common.certs.is_valid_pemfile',
                                new_callable=mock.MagicMock,
                                return_value=True):
                    self.eb._download_client_certificates()

        def check(*args):
            with open(cert_path, "r") as c:
                self.assertNotEqual(c.read(), old_cert_content)
        d = threads.deferToThread(wrapper)
        d.addCallback(check)

        return d

    @deferred()
    def test_download_client_certificate_invalid_download(self):
        cert_path, _ = self._download_certificate_test_template(
            False, False)

        def wrapper(*args):
            with mock.patch('leap.common.certs.should_redownload',
                            new_callable=mock.MagicMock,
                            return_value=True):
                with mock.patch('leap.common.certs.is_valid_pemfile',
                                new_callable=mock.MagicMock,
                                return_value=False):
                    with self.assertRaises(Exception):
                        self.eb._download_client_certificates()
        d = threads.deferToThread(wrapper)

        return d

    @deferred()
    def test_download_client_certificate_uses_session_id(self):
        _, _ = self._download_certificate_test_template(
            False, False)

        SRPAuth.get_session_id = mock.MagicMock(return_value="1")

        def check_cookie(*args, **kwargs):
            cookies = kwargs.get("cookies", None)
            self.assertEqual(cookies, {'_session_id': '1'})
            return Response()

        def wrapper(*args):
            with mock.patch('leap.common.certs.should_redownload',
                            new_callable=mock.MagicMock,
                            return_value=False):
                with mock.patch('leap.common.certs.is_valid_pemfile',
                                new_callable=mock.MagicMock,
                                return_value=True):
                    with mock.patch('requests.sessions.Session.get',
                                    new_callable=mock.MagicMock,
                                    side_effect=check_cookie):
                        with mock.patch('requests.models.Response.content',
                                        new_callable=mock.PropertyMock,
                                        return_value="A"):
                            self.eb._download_client_certificates()

        d = threads.deferToThread(wrapper)

        return d

    @deferred()
    def test_run_eip_setup_checks(self):
        self.eb._download_config = mock.MagicMock()
        self.eb._download_client_certificates = mock.MagicMock()

        d = self.eb.run_eip_setup_checks(ProviderConfig())

        def check(*args):
            self.eb._download_config.assert_called_once_with()
            self.eb._download_client_certificates.assert_called_once_with(None)
        d.addCallback(check)
        return d
