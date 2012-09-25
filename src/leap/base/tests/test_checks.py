try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os

from mock import (patch, Mock)
from StringIO import StringIO

import ping
import requests

from leap.base import checks
from leap.base import exceptions
from leap.testing.basetest import BaseLeapTest

_uid = os.getuid()


class LeapNetworkCheckTest(BaseLeapTest):
    __name__ = "leap_network_check_tests"

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_checker_should_implement_check_methods(self):
        checker = checks.LeapNetworkChecker()

        self.assertTrue(hasattr(checker, "check_internet_connection"),
                        "missing meth")
        self.assertTrue(hasattr(checker, "is_internet_up"),
                        "missing meth")
        self.assertTrue(hasattr(checker, "ping_gateway"),
                        "missing meth")

    def test_checker_should_actually_call_all_tests(self):
        checker = checks.LeapNetworkChecker()

        mc = Mock()
        checker.run_all(checker=mc)
        self.assertTrue(mc.check_internet_connection.called, "not called")
        self.assertTrue(mc.ping_gateway.called, "not called")
        self.assertTrue(mc.is_internet_up.called, "not called")

    def test_get_default_interface_no_interface(self):
        checker = checks.LeapNetworkChecker()
        with patch('leap.base.checks.open', create=True) as mock_open:
            with self.assertRaises(exceptions.NoDefaultInterfaceFoundError):
                mock_open.return_value = StringIO(
                    "Iface\tDestination Gateway\t"
                    "Flags\tRefCntd\tUse\tMetric\t"
                    "Mask\tMTU\tWindow\tIRTT")
                checker.get_default_interface_gateway()

    def test_ping_gateway_fail(self):
        checker = checks.LeapNetworkChecker()
        with patch.object(ping, "quiet_ping") as mocked_ping:
            with self.assertRaises(exceptions.NoConnectionToGateway):
                mocked_ping.return_value = [11, "", ""]
                checker.ping_gateway("4.2.2.2")

    def test_check_internet_connection_failures(self):
        checker = checks.LeapNetworkChecker()
        with patch.object(requests, "get") as mocked_get:
            mocked_get.side_effect = requests.HTTPError
            with self.assertRaises(exceptions.NoInternetConnection):
                checker.check_internet_connection()

        with patch.object(requests, "get") as mocked_get:
            mocked_get.side_effect = requests.RequestException
            with self.assertRaises(exceptions.NoInternetConnection):
                checker.check_internet_connection()

        #TODO: Mock possible errors that can be raised by is_internet_up
        with patch.object(requests, "get") as mocked_get:
            mocked_get.side_effect = requests.ConnectionError
            with self.assertRaises(exceptions.NoInternetConnection):
                checker.check_internet_connection()

    @unittest.skipUnless(_uid == 0, "root only")
    def test_ping_gateway(self):
        checker = checks.LeapNetworkChecker()
        checker.ping_gateway("4.2.2.2")
