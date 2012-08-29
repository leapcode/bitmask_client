import ConfigParser
import os
import platform

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from leap.base import constants
from leap.eip import config as eip_config
from leap.testing.basetest import BaseLeapTest

_system = platform.system()


class EIPConfigTest(BaseLeapTest):

    __name__ = "eip_config_tests"

    def setUp(self):
        pass

    def tearDown(self):
        pass

    #
    # helpers
    #

    def touch_exec(self):
        tfile = os.path.join(
            self.tempfile,
            'bin',
            'openvpn')
        open(tfile, 'bw').close()

    def get_empty_config(self):
        _config = ConfigParser.ConfigParser()
        return _config

    def get_minimal_config(self):
        _config = ConfigParser.ConfigParser()
        return _config

    def get_expected_openvpn_args(self):
        args = []
        username = self.get_username()
        groupname = self.get_groupname()

        args.append('--user')
        args.append(username)
        args.append('--group')
        args.append(groupname)
        args.append('--management-client-user')
        args.append(username)
        args.append('--management-signal')
        args.append('--management')

        #XXX hey!
        #get platform switches here!
        args.append('/tmp/.eip.sock')
        args.append('unix')
        args.append('--config')
        args.append(os.path.expanduser(
            '~/.config/leap/providers/%s/openvpn.conf'
            % constants.DEFAULT_TEST_PROVIDER))
        return args

    # build command string
    # these tests are going to have to check
    # many combinations. we should inject some
    # params in the function call, to disable
    # some checks.

    def test_build_ovpn_command_empty_config(self):
        _config = self.get_empty_config()
        command, args = eip_config.build_ovpn_command(
            _config,
            do_pkexec_check=False)
        self.assertEqual(command, 'openvpn')
        self.assertEqual(args, self.get_expected_openvpn_args())

    # XXX TODO:
    # - should use touch_exec to plant an "executable" in the path
    # - should check that "which" for openvpn returns what's expected.


if __name__ == "__main__":
    unittest.main()
