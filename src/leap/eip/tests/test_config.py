import json
import os
import platform
import stat

try:
    import unittest2 as unittest
except ImportError:
    import unittest

#from leap.base import constants
#from leap.eip import config as eip_config
from leap import __branding as BRANDING
from leap.eip import config as eipconfig
from leap.eip.tests.data import EIP_SAMPLE_CONFIG, EIP_SAMPLE_SERVICE
from leap.testing.basetest import BaseLeapTest
from leap.util.fileutil import mkdir_p

_system = platform.system()

PROVIDER = BRANDING.get('provider_domain')
PROVIDER_SHORTNAME = BRANDING.get('short_name')


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
        path = os.path.join(
            self.tempdir, 'bin')
        mkdir_p(path)
        tfile = os.path.join(
            path,
            'openvpn')
        open(tfile, 'wb').close()
        os.chmod(tfile, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

    def write_sample_eipservice(self):
        conf = eipconfig.EIPServiceConfig()
        folder, f = os.path.split(conf.filename)
        if not os.path.isdir(folder):
            mkdir_p(folder)
        with open(conf.filename, 'w') as fd:
            fd.write(json.dumps(EIP_SAMPLE_SERVICE))

    def write_sample_eipconfig(self):
        conf = eipconfig.EIPConfig()
        folder, f = os.path.split(conf.filename)
        if not os.path.isdir(folder):
            mkdir_p(folder)
        with open(conf.filename, 'w') as fd:
            fd.write(json.dumps(EIP_SAMPLE_CONFIG))

    def get_expected_openvpn_args(self):
        args = []
        username = self.get_username()
        groupname = self.get_groupname()

        args.append('--client')
        args.append('--dev')
        #does this have to be tap for win??
        args.append('tun')
        args.append('--persist-tun')
        args.append('--persist-key')
        args.append('--remote')
        args.append('%s' % eipconfig.get_eip_gateway())
        # XXX get port!?
        args.append('1194')
        # XXX get proto
        args.append('udp')
        args.append('--tls-client')
        args.append('--remote-cert-tls')
        args.append('server')

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
        args.append('/tmp/test.socket')
        args.append('unix')

        # certs
        # XXX get values from specs?
        args.append('--cert')
        args.append(os.path.join(
            self.home,
            '.config', 'leap', 'providers',
            '%s' % PROVIDER,
            'keys', 'client',
            'openvpn.pem'))
        args.append('--key')
        args.append(os.path.join(
            self.home,
            '.config', 'leap', 'providers',
            '%s' % PROVIDER,
            'keys', 'client',
            'openvpn.pem'))
        args.append('--ca')
        args.append(os.path.join(
            self.home,
            '.config', 'leap', 'providers',
            '%s' % PROVIDER,
            'keys', 'ca',
            '%s-cacert.pem' % PROVIDER_SHORTNAME))
        return args

    # build command string
    # these tests are going to have to check
    # many combinations. we should inject some
    # params in the function call, to disable
    # some checks.

    def test_build_ovpn_command_empty_config(self):
        self.touch_exec()
        self.write_sample_eipservice()
        self.write_sample_eipconfig()

        from leap.eip import config as eipconfig
        from leap.util.fileutil import which
        path = os.environ['PATH']
        vpnbin = which('openvpn', path=path)
        print 'path =', path
        print 'vpnbin = ', vpnbin
        command, args = eipconfig.build_ovpn_command(
            do_pkexec_check=False, vpnbin=vpnbin,
            socket_path="/tmp/test.socket")
        self.assertEqual(command, self.home + '/bin/openvpn')
        self.assertEqual(args, self.get_expected_openvpn_args())


if __name__ == "__main__":
    unittest.main()
