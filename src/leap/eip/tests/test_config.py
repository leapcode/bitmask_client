import ConfigParser
import os
import platform
import shutil
import socket
import tempfile

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from leap.eip import config

_system = platform.system()


class NotImplementedError(Exception):
    pass

# XXX use mock_open here?


class EIPConfigTest(unittest.TestCase):

    __name__ = "eip_config_tests"

    def setUp(self):
        self.old_path = os.environ['PATH']

        self.tdir = tempfile.mkdtemp()

        bin_tdir = os.path.join(
            self.tdir,
            'bin')
        os.mkdir(bin_tdir)
        os.environ['PATH'] = bin_tdir

    def tearDown(self):
        os.environ['PATH'] = self.old_path
        shutil.rmtree(self.tdir)
    #
    # helpers
    #

    def get_username(self):
        return config.get_username()

    def get_groupname(self):
        return config.get_groupname()

    def _missing_test_for_plat(self, do_raise=False):
        if do_raise:
            raise NotImplementedError(
                "This test is not implemented "
                "for the running platform: %s" %
                _system)

    def touch_exec(self):
        tfile = os.path.join(
            self.tdir,
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
        #XXX bad assumption. FIXME: expand $HOME
        args.append('/home/%s/.config/leap/providers/default/openvpn.conf' %
                    username)
        return args

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
            self.get_username())

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
            self.get_username())

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

    # build command string
    # these tests are going to have to check
    # many combinations. we should inject some
    # params in the function call, to disable
    # some checks.
    # XXX breaking!

    def test_build_ovpn_command_empty_config(self):
        _config = self.get_empty_config()
        command, args = config.build_ovpn_command(
            _config,
            do_pkexec_check=False)
        self.assertEqual(command, 'openvpn')
        self.assertEqual(args, self.get_expected_openvpn_args())


if __name__ == "__main__":
    unittest.main()
