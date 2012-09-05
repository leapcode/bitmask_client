import logging
import platform
import os

logging.basicConfig()
logger = logging.getLogger(name=__name__)

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from mock import Mock, patch  # MagicMock

from leap.eip.eipconnection import EIPConnection
from leap.eip.exceptions import ConnectionRefusedError
from leap.eip import specs as eipspecs
from leap.testing.basetest import BaseLeapTest

_system = platform.system()


class NotImplementedError(Exception):
    pass


@patch('OpenVPNConnection._get_or_create_config')
@patch('OpenVPNConnection._set_ovpn_command')
class MockedEIPConnection(EIPConnection):
    def _set_ovpn_command(self):
        self.command = "mock_command"
        self.args = [1, 2, 3]


class EIPConductorTest(BaseLeapTest):

    __name__ = "eip_conductor_tests"

    def setUp(self):
        # XXX there's a conceptual/design
        # mistake here.
        # If we're testing just attrs after init,
        # init shold not be doing so much side effects.

        # for instance:
        # We have to TOUCH a keys file because
        # we're triggerig the key checks FROM
        # the constructor. me not like that,
        # key checker should better be called explicitelly.

        # XXX change to keys_checker invocation
        # (see config_checker)

        keyfiles = (eipspecs.provider_ca_path(),
                    eipspecs.client_cert_path())
        for filepath in keyfiles:
            self.touch(filepath)
            self.chmod600(filepath)

        # we init the manager with only
        # some methods mocked
        self.manager = Mock(name="openvpnmanager_mock")
        self.con = MockedEIPConnection()
        self.con.run_openvpn_checks()

    def tearDown(self):
        del self.con

    #
    # tests
    #

    def test_vpnconnection_defaults(self):
        """
        default attrs as expected
        """
        con = self.con
        self.assertEqual(con.autostart, True)

    def test_ovpn_command(self):
        """
        set_ovpn_command called
        """
        self.assertEqual(self.con.command,
                         "mock_command")
        self.assertEqual(self.con.args,
                         [1, 2, 3])

    # config checks

    def test_config_checked_called(self):
        del(self.con)
        config_checker = Mock()
        self.con = MockedEIPConnection(config_checker=config_checker)
        self.assertTrue(config_checker.called)
        self.con.run_checks()
        self.con.config_checker.run_all.assert_called_with(skip_download=False)

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
