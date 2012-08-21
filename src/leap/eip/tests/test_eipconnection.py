import ConfigParser
import logging
import platform

logging.basicConfig()
logger = logging.getLogger(name=__name__)

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from mock import Mock, patch  # MagicMock

from leap.eip.eipconnection import EIPConnection
from leap.eip.exceptions import ConnectionRefusedError

_system = platform.system()


class NotImplementedError(Exception):
    pass


@patch('OpenVPNConnection._get_or_create_config')
@patch('OpenVPNConnection._set_ovpn_command')
class MockedEIPConnection(EIPConnection):
    def _get_or_create_config(self):
        self.config = ConfigParser.ConfigParser()
        self._set_ovpn_command()

    def _set_ovpn_command(self):
        self.command = "mock_command"
        self.args = [1, 2, 3]


class EIPConductorTest(unittest.TestCase):

    __name__ = "eip_conductor_tests"

    def setUp(self):
        self.manager = Mock(
            name="openvpnmanager_mock")

        self.con = MockedEIPConnection()
            #manager=self.manager)

    def tearDown(self):
        del self.con

    #
    # helpers
    #

    def _missing_test_for_plat(self, do_raise=False):
        if do_raise:
            raise NotImplementedError(
                "This test is not implemented "
                "for the running platform: %s" %
                _system)

    #
    # tests
    #

    @unittest.skip
    #ain't manager anymore!
    def test_manager_was_initialized(self):
        """
        manager init ok during conductor init?
        """
        self.manager.assert_called_once_with()

    def test_vpnconnection_defaults(self):
        """
        default attrs as expected
        """
        con = self.con
        self.assertEqual(con.autostart, True)
        self.assertEqual(con.missing_pkexec, False)
        self.assertEqual(con.missing_vpn_keyfile, False)
        self.assertEqual(con.missing_provider, False)
        self.assertEqual(con.bad_provider, False)

    def test_config_was_init(self):
        """
        is there a config object?
        """
        self.assertTrue(isinstance(self.con.config,
                        ConfigParser.ConfigParser))

    def test_ovpn_command(self):
        """
        set_ovpn_command called
        """
        self.assertEqual(self.con.command,
                         "mock_command")
        self.assertEqual(self.con.args,
                         [1, 2, 3])

    # connect/disconnect calls

    def test_disconnect(self):
        """
        disconnect method calls private and changes status
        """
        self.con._disconnect = Mock(
            name="_disconnect")

        # first we set status to connected
        self.con.status.set_current(self.con.status.CONNECTED)
        self.assertEqual(self.con.status.current,
                         self.con.status.CONNECTED)

        # disconnect
        self.con.disconnect()
        self.con._disconnect.assert_called_once_with()

        # new status should be disconnected
        # XXX this should evolve and check no errors
        # during disconnection
        self.assertEqual(self.con.status.current,
                         self.con.status.DISCONNECTED)

    def test_connect(self):
        """
        connect calls _launch_openvpn private
        """
        self.con._launch_openvpn = Mock()
        self.con.connect()
        self.con._launch_openvpn.assert_called_once_with()

    # XXX tests breaking here ...

    def test_good_poll_connection_state(self):
        """
        """
        #@patch --
        # self.manager.get_connection_state

        #XXX review this set of poll_state tests
        #they SHOULD NOT NEED TO MOCK ANYTHING IN THE
        #lower layers!! -- status, vpn_manager..
        #right now we're testing implementation, not
        #behavior!!!
        good_state = ["1345466946", "unknown_state", "ok",
                      "192.168.1.1", "192.168.1.100"]
        self.con.get_connection_state = Mock(return_value=good_state)
        self.con.status.set_vpn_state = Mock()

        state = self.con.poll_connection_state()
        good_state[1] = "disconnected"
        final_state = tuple(good_state)
        self.con.status.set_vpn_state.assert_called_with("unknown_state")
        self.assertEqual(state, final_state)

    # TODO between "good" and "bad" (exception raised) cases,
    # we can still test for malformed states and see that only good
    # states do have a change (and from only the expected transition
    # states).

    def test_bad_poll_connection_state(self):
        """
        get connection state raises ConnectionRefusedError
        state is None
        """
        self.con.get_connection_state = Mock(
            side_effect=ConnectionRefusedError('foo!'))
        state = self.con.poll_connection_state()
        self.assertEqual(state, None)


    # XXX more things to test:
    # - called config routines during initz.
    # - raising proper exceptions with no config
    # - called proper checks on config / permissions


if __name__ == "__main__":
    unittest.main()
