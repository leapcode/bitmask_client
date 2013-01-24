from collections import OrderedDict
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
#from leap import __branding as BRANDING
from leap.eip import config as eipconfig
from leap.eip.tests.data import EIP_SAMPLE_CONFIG, EIP_SAMPLE_SERVICE
from leap.testing.basetest import BaseLeapTest
from leap.util.fileutil import mkdir_p, mkdir_f

_system = platform.system()

#PROVIDER = BRANDING.get('provider_domain')
#PROVIDER_SHORTNAME = BRANDING.get('short_name')


class EIPConfigTest(BaseLeapTest):

    __name__ = "eip_config_tests"
    provider = "testprovider.example.org"

    maxDiff = None

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

    def write_sample_eipservice(self, vpnciphers=False, extra_vpnopts=None,
                                gateways=None):
        conf = eipconfig.EIPServiceConfig()
        mkdir_f(conf.filename)
        if gateways:
            EIP_SAMPLE_SERVICE['gateways'] = gateways
        if vpnciphers:
            openvpnconfig = OrderedDict({
                "auth": "SHA1",
                "cipher": "AES-128-CBC",
                "tls-cipher": "DHE-RSA-AES128-SHA"})
            if extra_vpnopts:
                for k, v in extra_vpnopts.items():
                    openvpnconfig[k] = v
            EIP_SAMPLE_SERVICE['openvpn_configuration'] = openvpnconfig

        with open(conf.filename, 'w') as fd:
            fd.write(json.dumps(EIP_SAMPLE_SERVICE))

    def write_sample_eipconfig(self):
        conf = eipconfig.EIPConfig()
        folder, f = os.path.split(conf.filename)
        if not os.path.isdir(folder):
            mkdir_p(folder)
        with open(conf.filename, 'w') as fd:
            fd.write(json.dumps(EIP_SAMPLE_CONFIG))

    def get_expected_openvpn_args(self, with_openvpn_ciphers=False):
        """
        yeah, this is almost as duplicating the
        code for building the command
        """
        args = []
        eipconf = eipconfig.EIPConfig(domain=self.provider)
        eipconf.load()
        eipsconf = eipconfig.EIPServiceConfig(domain=self.provider)
        eipsconf.load()

        username = self.get_username()
        groupname = self.get_groupname()

        args.append('--client')
        args.append('--dev')
        #does this have to be tap for win??
        args.append('tun')
        args.append('--persist-tun')
        args.append('--persist-key')
        args.append('--remote')

        args.append('%s' % eipconfig.get_eip_gateway(
            eipconfig=eipconf,
            eipserviceconfig=eipsconf))
        # XXX get port!?
        args.append('1194')
        # XXX get proto
        args.append('udp')
        args.append('--tls-client')
        args.append('--remote-cert-tls')
        args.append('server')

        if with_openvpn_ciphers:
            CIPHERS = [
                "--tls-cipher", "DHE-RSA-AES128-SHA",
                "--cipher", "AES-128-CBC",
                "--auth", "SHA1"]
            for opt in CIPHERS:
                args.append(opt)

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

        args.append('--script-security')
        args.append('2')

        if _system == "Linux":
            args.append('--up')
            args.append('/etc/leap/resolv-update')
            args.append('--down')
            args.append('/etc/leap/resolv-update')
            args.append('--plugin')
            args.append('/usr/lib/openvpn/openvpn-down-root.so')
            args.append("'script_type=down /etc/leap/resolv-update'")

        # certs
        # XXX get values from specs?
        args.append('--cert')
        args.append(os.path.join(
            self.home,
            '.config', 'leap', 'providers',
            '%s' % self.provider,
            'keys', 'client',
            'openvpn.pem'))
        args.append('--key')
        args.append(os.path.join(
            self.home,
            '.config', 'leap', 'providers',
            '%s' % self.provider,
            'keys', 'client',
            'openvpn.pem'))
        args.append('--ca')
        args.append(os.path.join(
            self.home,
            '.config', 'leap', 'providers',
            '%s' % self.provider,
            'keys', 'ca',
            'cacert.pem'))
        return args

    # build command string
    # these tests are going to have to check
    # many combinations. we should inject some
    # params in the function call, to disable
    # some checks.

    def test_get_eip_gateway(self):
        self.write_sample_eipconfig()
        eipconf = eipconfig.EIPConfig(domain=self.provider)

        # default eipservice
        self.write_sample_eipservice()
        eipsconf = eipconfig.EIPServiceConfig(domain=self.provider)

        gateway = eipconfig.get_eip_gateway(
            eipconfig=eipconf,
            eipserviceconfig=eipsconf)

        # in spec is local gateway by default
        self.assertEqual(gateway, '127.0.0.1')

        # change eipservice
        # right now we only check that cluster == selected primary gw in
        # eip.json, and pick first matching ip
        eipconf._config.config['primary_gateway'] = "foo_provider"
        newgateways = [{"cluster": "foo_provider",
                        "ip_address": "127.0.0.99"}]
        self.write_sample_eipservice(gateways=newgateways)
        eipsconf = eipconfig.EIPServiceConfig(domain=self.provider)
        # load from disk file
        eipsconf.load()

        gateway = eipconfig.get_eip_gateway(
            eipconfig=eipconf,
            eipserviceconfig=eipsconf)
        self.assertEqual(gateway, '127.0.0.99')

        # change eipservice, several gateways
        # right now we only check that cluster == selected primary gw in
        # eip.json, and pick first matching ip
        eipconf._config.config['primary_gateway'] = "bar_provider"
        newgateways = [{"cluster": "foo_provider",
                        "ip_address": "127.0.0.99"},
                       {'cluster': "bar_provider",
                        "ip_address": "127.0.0.88"}]
        self.write_sample_eipservice(gateways=newgateways)
        eipsconf = eipconfig.EIPServiceConfig(domain=self.provider)
        # load from disk file
        eipsconf.load()

        gateway = eipconfig.get_eip_gateway(
            eipconfig=eipconf,
            eipserviceconfig=eipsconf)
        self.assertEqual(gateway, '127.0.0.88')

    def test_build_ovpn_command_empty_config(self):
        self.touch_exec()
        self.write_sample_eipservice()
        self.write_sample_eipconfig()

        from leap.eip import config as eipconfig
        from leap.util.fileutil import which
        path = os.environ['PATH']
        vpnbin = which('openvpn', path=path)
        #print 'path =', path
        #print 'vpnbin = ', vpnbin
        vpncommand, vpnargs = eipconfig.build_ovpn_command(
            do_pkexec_check=False, vpnbin=vpnbin,
            socket_path="/tmp/test.socket",
            provider=self.provider)
        self.assertEqual(vpncommand, self.home + '/bin/openvpn')
        self.assertEqual(vpnargs, self.get_expected_openvpn_args())

    def test_build_ovpn_command_openvpnoptions(self):
        self.touch_exec()

        from leap.eip import config as eipconfig
        from leap.util.fileutil import which
        path = os.environ['PATH']
        vpnbin = which('openvpn', path=path)

        self.write_sample_eipconfig()

        # regular run, everything normal
        self.write_sample_eipservice(vpnciphers=True)
        vpncommand, vpnargs = eipconfig.build_ovpn_command(
            do_pkexec_check=False, vpnbin=vpnbin,
            socket_path="/tmp/test.socket",
            provider=self.provider)
        self.assertEqual(vpncommand, self.home + '/bin/openvpn')
        expected = self.get_expected_openvpn_args(
            with_openvpn_ciphers=True)
        self.assertEqual(vpnargs, expected)

        # bad options -- illegal options
        self.write_sample_eipservice(
            vpnciphers=True,
            # WE ONLY ALLOW vpn options in auth, cipher, tls-cipher
            extra_vpnopts={"notallowedconfig": "badvalue"})
        vpncommand, vpnargs = eipconfig.build_ovpn_command(
            do_pkexec_check=False, vpnbin=vpnbin,
            socket_path="/tmp/test.socket",
            provider=self.provider)
        self.assertEqual(vpncommand, self.home + '/bin/openvpn')
        expected = self.get_expected_openvpn_args(
            with_openvpn_ciphers=True)
        self.assertEqual(vpnargs, expected)

        # bad options -- illegal chars
        self.write_sample_eipservice(
            vpnciphers=True,
            # WE ONLY ALLOW A-Z09\-
            extra_vpnopts={"cipher": "AES-128-CBC;FOOTHING"})
        vpncommand, vpnargs = eipconfig.build_ovpn_command(
            do_pkexec_check=False, vpnbin=vpnbin,
            socket_path="/tmp/test.socket",
            provider=self.provider)
        self.assertEqual(vpncommand, self.home + '/bin/openvpn')
        expected = self.get_expected_openvpn_args(
            with_openvpn_ciphers=True)
        self.assertEqual(vpnargs, expected)


if __name__ == "__main__":
    unittest.main()
