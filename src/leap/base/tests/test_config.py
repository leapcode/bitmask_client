import os
import platform
import socket
import tempfile

import mock
import requests

from leap.base import config
from leap.testing.basetest import BaseLeapTest


try:
    import unittest2 as unittest
except ImportError:
    import unittest

_system = platform.system()


class DefinitionTestCase(BaseLeapTest):

    # XXX See how to merge with test_providers
    # -- kali 2012-08-24 00:38

    __name__ = "provider_config_tests"

    def setUp(self):
        self.old_home = os.environ['HOME']
        self.home = tempfile.mkdtemp()
        os.environ['HOME'] = self.home
        pass

    #Not correct removing the test directories but will be refactor out
    #with kali's new test classes
    def tearDown(self):
        os.environ['HOME'] = self.old_home
        pass

    def test_complete_file(self):
        with mock.patch.object(requests, "get") as mock_method:
            mock_method.return_value.status_code = 200
            mock_method.return_value.json = {
                u'api_uri': u'https://api.testprovider.org/',
                u'api_version': u'0.1.0',
                u'ca_cert': u'8aab80ae4326fd30721689db813733783fe0bd7e',
                u'ca_cert_uri': u'https://testprovider.org/cacert.pem',
                u'description': {u'en': u'This is a test provider'},
                u'display_name': {u'en': u'Test Provider'},
                u'domain': u'testprovider.org',
                u'enrollment_policy': u'open',
                u'public_key': u'cb7dbd679f911e85bc2e51bd44afd7308ee19c21',
                u'serial': 1,
                u'services': [u'eip'],
                u'version': u'0.1.0'}
            cf = config.Configuration("http://localhost/")
            self.assertIn('default', cf.providers)

    def test_connection_error(self):
        with mock.patch.object(requests, "get") as mock_method:
            mock_method.side_effect = requests.ConnectionError
            cf = config.Configuration()
            self.assertIsInstance(cf.error, str)

    def test_file_not_found(self):
        with mock.patch.object(requests, "get") as mock_method:
            mock_method.side_effect = requests.HTTPError
            cf = config.Configuration()
            self.assertIsInstance(cf.error, str)

    def test_invalid_url(self):
        cf = config.Configuration("ht")
        self.assertTrue(cf.error)


class ConfigHelperFunctions(BaseLeapTest):

    __name__ = "config_helper_tests"

    def setUp(self):
        pass

    def tearDown(self):
        pass

    #
    # tests
    #

    # XXX fixme! /home/user should
    # be replaced for proper home lookup.

    @unittest.skipUnless(_system == "Linux", "linux only")
    def test_lin_get_config_file(self):
        """
        config file path where expected? (linux)
        """
        self.assertEqual(
            config.get_config_file(
                'test', folder="foo/bar"),
            '/home/%s/.config/leap/foo/bar/test' %
            config.get_username())

    @unittest.skipUnless(_system == "Darwin", "mac only")
    def test_mac_get_config_file(self):
        """
        config file path where expected? (mac)
        """
        self._missing_test_for_plat(do_raise=True)

    @unittest.skipUnless(_system == "Windows", "win only")
    def test_win_get_config_file(self):
        """
        config file path where expected?
        """
        self._missing_test_for_plat(do_raise=True)

    #
    # XXX hey, I'm raising exceptions here
    # on purpose. just wanted to make sure
    # that the skip stuff is doing it right.
    # If you're working on win/macos tests,
    # feel free to remove tests that you see
    # are too redundant.

    @unittest.skipUnless(_system == "Linux", "linux only")
    def test_lin_get_config_dir(self):
        """
        nice config dir? (linux)
        """
        self.assertEqual(
            config.get_config_dir(),
            #XXX not correct!!!
            #hardcoded home
            '/home/%s/.config/leap' %
            self.get_username())

    @unittest.skipUnless(_system == "Darwin", "mac only")
    def test_mac_get_config_dir(self):
        """
        nice config dir? (mac)
        """
        self._missing_test_for_plat(do_raise=True)

    @unittest.skipUnless(_system == "Windows", "win only")
    def test_win_get_config_dir(self):
        """
        nice config dir? (win)
        """
        self._missing_test_for_plat(do_raise=True)

    # provider paths

    @unittest.skipUnless(_system == "Linux", "linux only")
    def test_get_default_provider_path(self):
        """
        is default provider path ok?
        """
        self.assertEqual(
            config.get_default_provider_path(),
            '/home/%s/.config/leap/providers/default/' %
            config.get_username())

    # validate ip

    def test_validate_ip(self):
        """
        check our ip validation
        """
        config.validate_ip('3.3.3.3')
        with self.assertRaises(socket.error):
            config.validate_ip('255.255.255.256')
        with self.assertRaises(socket.error):
            config.validate_ip('foobar')

    @unittest.skip
    def test_validate_domain(self):
        """
        code to be written yet
        """
        pass


if __name__ == "__main__":
    unittest.main()
