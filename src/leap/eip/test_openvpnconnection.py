import logging
import platform
#import socket

logging.basicConfig()
logger = logging.getLogger(name=__name__)

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from mock import Mock, patch  # MagicMock

from leap.eip import openvpnconnection
from leap.eip import exceptions as eip_exceptions
from leap.eip.udstelnet import UDSTelnet

_system = platform.system()


class NotImplementedError(Exception):
    pass


mock_UDSTelnet = Mock(spec=UDSTelnet)
# XXX cautious!!!
# this might be fragile right now (counting a global
# reference of calls I think.
# investigate this other form instead:
# http://www.voidspace.org.uk/python/mock/patch.html#start-and-stop

# XXX redo after merge-refactor


@patch('openvpnconnection.OpenVPNConnection.connect_to_management')
class MockedOpenVPNConnection(openvpnconnection.OpenVPNConnection):
    def __init__(self, *args, **kwargs):
        self.mock_UDSTelnet = Mock()
        super(MockedOpenVPNConnection, self).__init__(
            *args, **kwargs)
        self.tn = self.mock_UDSTelnet(self.host, self.port)

    def connect_to_management(self):
        #print 'patched connect'
        self.tn = mock_UDSTelnet(self.host, port=self.port)


class OpenVPNConnectionTest(unittest.TestCase):

    __name__ = "vpnconnection_tests"

    def setUp(self):
        self.manager = MockedOpenVPNConnection()

    def tearDown(self):
        del self.manager

    #
    # helpers
    #

    # XXX hey, refactor this to basetestclass

    def _missing_test_for_plat(self, do_raise=False):
        if do_raise:
            raise NotImplementedError(
                "This test is not implemented "
                "for the running platform: %s" %
                _system)

    #
    # tests
    #

    @unittest.skipIf(_system == "Windows", "lin/mac only")
    def test_lin_mac_default_init(self):
        """
        check default host for management iface
        """
        self.assertEqual(self.manager.host, '/tmp/.eip.sock')
        self.assertEqual(self.manager.port, 'unix')

    @unittest.skipUnless(_system == "Windows", "win only")
    def test_win_default_init(self):
        """
        check default host for management iface
        """
        # XXX should we make the platform specific switch
        # here or in the vpn command string building?
        self.assertEqual(self.manager.host, 'localhost')
        self.assertEqual(self.manager.port, 7777)

    def test_port_types_init(self):
        self.manager = MockedOpenVPNConnection(port="42")
        self.assertEqual(self.manager.port, 42)
        self.manager = MockedOpenVPNConnection()
        self.assertEqual(self.manager.port, "unix")
        self.manager = MockedOpenVPNConnection(port="bad")
        self.assertEqual(self.manager.port, None)

    def test_connect_raises_missing_socket(self):
        self.manager = openvpnconnection.OpenVPNConnection()
        with self.assertRaises(eip_exceptions.MissingSocketError):
            self.manager.connect_to_management()

    def test_uds_telnet_called_on_connect(self):
        self.manager.connect()
        mock_UDSTelnet.assert_called_with(
            self.manager.host,
            port=self.manager.port)

    @unittest.skip
    def test_connect(self):
        raise NotImplementedError
        # XXX calls close
        # calls UDSTelnet mock.

    # XXX
    # tests to write:
    # UDSTelnetTest (for real?)
    # HAVE A LOOK AT CORE TESTS FOR TELNETLIB.
    # very illustrative instead...

    # - raise MissingSocket
    # - raise ConnectionRefusedError
    # - test send command
    #   - tries connect
    #   - ... tries?
    #   - ... calls _seek_to_eof
    #   - ... read_until --> return value
    #   - ...


if __name__ == "__main__":
    unittest.main()
