# -*- coding: utf-8 -*-
# vpnlaunchers.py
# Copyright (C) 2013 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Platform dependant VPN launchers
"""
import commands
import logging
import getpass
import os
import platform
try:
    import grp
except ImportError:
    pass  # ignore, probably windows

from abc import ABCMeta, abstractmethod

from leap.common.check import leap_assert, leap_assert_type
from leap.common.files import which
from leap.config.providerconfig import ProviderConfig
from leap.services.eip.eipconfig import EIPConfig

logger = logging.getLogger(__name__)


class VPNLauncherException(Exception):
    pass


class OpenVPNNotFoundException(VPNLauncherException):
    pass


class EIPNoPolkitAuthAgentAvailable(VPNLauncherException):
    pass


class EIPNoPkexecAvailable(VPNLauncherException):
    pass


class VPNLauncher:
    """
    Abstract launcher class
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def get_vpn_command(self, eipconfig=None, providerconfig=None,
                        socket_host=None, socket_port=None):
        """
        Returns the platform dependant vpn launching command

        :param eipconfig: eip configuration object
        :type eipconfig: EIPConfig
        :param providerconfig: provider specific configuration
        :type providerconfig: ProviderConfig
        :param socket_host: either socket path (unix) or socket IP
        :type socket_host: str
        :param socket_port: either string "unix" if it's a unix
        socket, or port otherwise
        :type socket_port: str

        :return: A VPN command ready to be launched
        :rtype: list
        """
        return []

    @abstractmethod
    def get_vpn_env(self, providerconfig):
        """
        Returns a dictionary with the custom env for the platform.
        This is mainly used for setting LD_LIBRARY_PATH to the correct
        path when distributing a standalone client

        :param providerconfig: provider specific configuration
        :type providerconfig: ProviderConfig

        :rtype: dict
        """
        return {}


def get_platform_launcher():
    launcher = globals()[platform.system() + "VPNLauncher"]
    leap_assert(launcher, "Unimplemented platform launcher: %s" %
                (platform.system(),))
    return launcher()


def _is_pkexec_in_system():
    pkexec_path = which('pkexec')
    if len(pkexec_path) == 0:
        return False
    return True


def _has_updown_scripts(path):
    """
    Checks the existence of the up/down scripts
    """
    # XXX should check permissions too
    is_file = os.path.isfile(path)
    if not is_file:
        logger.error("Could not find up/down scripts. " +
                     "Might produce DNS leaks.")
    return is_file


def _is_auth_agent_running():
    """
    Checks if a polkit daemon is running.

    :return: True if it's running, False if it's not.
    :rtype: boolean
    """
    polkit_gnome = 'ps aux | grep polkit-[g]nome-authentication-agent-1'
    polkit_kde = 'ps aux | grep polkit-[k]de-authentication-agent-1'
    return (len(commands.getoutput(polkit_gnome)) > 0 or
            len(commands.getoutput(polkit_kde)) > 0)


class LinuxVPNLauncher(VPNLauncher):
    """
    VPN launcher for the Linux platform
    """

    PKEXEC_BIN = 'pkexec'
    OPENVPN_BIN = 'openvpn'
    UP_DOWN_SCRIPT = "/etc/leap/resolv-update"
    OPENVPN_DOWN_ROOT = "/usr/lib/openvpn/openvpn-down-root.so"

    def get_vpn_command(self, eipconfig=None, providerconfig=None,
                        socket_host=None, socket_port="unix"):
        """
        Returns the platform dependant vpn launching command. It will
        look for openvpn in the regular paths and algo in
        path_prefix/apps/eip/ (in case standalone is set)

        Might raise VPNException.

        :param eipconfig: eip configuration object
        :type eipconfig: EIPConfig

        :param providerconfig: provider specific configuration
        :type providerconfig: ProviderConfig

        :param socket_host: either socket path (unix) or socket IP
        :type socket_host: str

        :param socket_port: either string "unix" if it's a unix
                            socket, or port otherwise
        :type socket_port: str

        :return: A VPN command ready to be launched
        :rtype: list
        """
        leap_assert(eipconfig, "We need an eip config")
        leap_assert_type(eipconfig, EIPConfig)
        leap_assert(providerconfig, "We need a provider config")
        leap_assert_type(providerconfig, ProviderConfig)
        leap_assert(socket_host, "We need a socket host!")
        leap_assert(socket_port, "We need a socket port!")

        kwargs = {}
        if ProviderConfig.standalone:
            kwargs['path_extension'] = os.path.join(
                providerconfig.get_path_prefix(),
                "..", "apps", "eip")

        openvpn_possibilities = which(
            self.OPENVPN_BIN,
            **kwargs)

        if len(openvpn_possibilities) == 0:
            raise OpenVPNNotFoundException()

        openvpn = openvpn_possibilities[0]
        args = []

        if _is_pkexec_in_system():
            if _is_auth_agent_running():
                pkexec_possibilities = which(self.PKEXEC_BIN)
                leap_assert(len(pkexec_possibilities) > 0,
                            "We couldn't find pkexec")
                args.append(openvpn)
                openvpn = pkexec_possibilities[0]
            else:
                logger.warning("No polkit auth agent found. pkexec " +
                               "will use its own auth agent.")
                raise EIPNoPolkitAuthAgentAvailable()
        else:
            logger.warning("System has no pkexec")
            raise EIPNoPkexecAvailable()

        # TODO: handle verbosity

        gateway_ip = str(eipconfig.get_gateway_ip(0))

        logger.debug("Using gateway ip %s" % (gateway_ip,))

        args += [
            '--client',
            '--dev', 'tun',
            '--persist-tun',
            '--persist-key',
            '--remote', gateway_ip, '1194', 'udp',
            '--tls-client',
            '--remote-cert-tls',
            'server'
        ]

        openvpn_configuration = eipconfig.get_openvpn_configuration()

        # FIXME: sanitize this! --
        for key, value in openvpn_configuration.items():
            args += ['--%s' % (key,), value]

        args += [
            '--user', getpass.getuser(),
            '--group', grp.getgrgid(os.getgroups()[-1]).gr_name
        ]

        if socket_port == "unix":
            args += [
                '--management-client-user', getpass.getuser()
            ]

        args += [
            '--management-signal',
            '--management', socket_host, socket_port,
            '--script-security', '2'
        ]

        if _has_updown_scripts(self.UP_DOWN_SCRIPT):
            args += [
                '--up', self.UP_DOWN_SCRIPT,
                '--down', self.UP_DOWN_SCRIPT,
                '--plugin', self.OPENVPN_DOWN_ROOT,
                '\'script_type=down %s\'' % self.UP_DOWN_SCRIPT
            ]

        args += [
            '--cert', eipconfig.get_client_cert_path(providerconfig),
            '--key', eipconfig.get_client_cert_path(providerconfig),
            '--ca', providerconfig.get_ca_cert_path()
        ]

        logger.debug("Running VPN with command:")
        logger.debug("%s %s" % (openvpn, " ".join(args)))

        return [openvpn] + args

    def get_vpn_env(self, providerconfig):
        """
        Returns a dictionary with the custom env for the platform.
        This is mainly used for setting LD_LIBRARY_PATH to the correct
        path when distributing a standalone client

        :param providerconfig: provider specific configuration
        :type providerconfig: ProviderConfig

        :rtype: dict
        """
        leap_assert(providerconfig, "We need a provider config")
        leap_assert_type(providerconfig, ProviderConfig)

        return {"LD_LIBRARY_PATH": os.path.join(
                providerconfig.get_path_prefix(),
                "..", "lib")}


class DarwinVPNLauncher(VPNLauncher):
    """
    VPN launcher for the Darwin Platform
    """

    OSASCRIPT_BIN = '/usr/bin/osascript'
    OSX_ASADMIN = "do shell script \"%s\" with administrator privileges"
    OPENVPN_BIN = 'openvpn.leap'
    INSTALL_PATH = "/Applications/LEAPClient.app/"
    # OPENVPN_BIN = "/%s/Contents/Resources/openvpn.leap" % (
    #   self.INSTALL_PATH,)
    UP_SCRIPT = "/%s/client.up.sh" % (INSTALL_PATH,)
    DOWN_SCRIPT = "/%s/client.down.sh" % (INSTALL_PATH,)

    # TODO: Add
    # OPENVPN_DOWN_ROOT = "/usr/lib/openvpn/openvpn-down-root.so"

    def get_vpn_command(self, eipconfig=None, providerconfig=None,
                        socket_host=None, socket_port="unix"):
        """
        Returns the platform dependant vpn launching command

        Might raise VPNException.

        :param eipconfig: eip configuration object
        :type eipconfig: EIPConfig

        :param providerconfig: provider specific configuration
        :type providerconfig: ProviderConfig

        :param socket_host: either socket path (unix) or socket IP
        :type socket_host: str

        :param socket_port: either string "unix" if it's a unix
                            socket, or port otherwise
        :type socket_port: str

        :return: A VPN command ready to be launched
        :rtype: list
        """
        leap_assert(eipconfig, "We need an eip config")
        leap_assert_type(eipconfig, EIPConfig)
        leap_assert(providerconfig, "We need a provider config")
        leap_assert_type(providerconfig, ProviderConfig)
        leap_assert(socket_host, "We need a socket host!")
        leap_assert(socket_port, "We need a socket port!")

        kwargs = {}
        if ProviderConfig.standalone:
            kwargs['path_extension'] = os.path.join(
                providerconfig.get_path_prefix(),
                "..", "apps", "eip")

        openvpn_possibilities = which(
            self.OPENVPN_BIN,
            **kwargs)
        if len(openvpn_possibilities) == 0:
            raise OpenVPNNotFoundException()

        openvpn = openvpn_possibilities[0]
        args = [openvpn]

        # TODO: handle verbosity

        gateway_ip = str(eipconfig.get_gateway_ip(0))
        logger.debug("Using gateway ip %s" % (gateway_ip,))

        args += [
            '--client',
            '--dev', 'tun',
            '--persist-tun',
            '--persist-key',
            '--remote', gateway_ip, '1194', 'udp',
            '--tls-client',
            '--remote-cert-tls',
            'server'
        ]

        # FIXME: sanitize this! --

        openvpn_configuration = eipconfig.get_openvpn_configuration()
        for key, value in openvpn_configuration.items():
            args += ['--%s' % (key,), value]

        args += [
            '--user', getpass.getuser(),
            '--group', grp.getgrgid(os.getgroups()[-1]).gr_name
        ]

        if socket_port == "unix":
            args += [
                '--management-client-user', getpass.getuser()
            ]

        args += [
            '--management-signal',
            '--management', socket_host, socket_port,
            '--script-security', '2'
        ]

        if _has_updown_scripts(self.UP_SCRIPT):
            args += [
                '--up', self.UP_SCRIPT,
            ]
        if _has_updown_scripts(self.DOWN_SCRIPT):
            args += [
                '--down', self.DOWN_SCRIPT,
                # FIXME add down-plugin
                # '--plugin', self.OPENVPN_DOWN_ROOT,
                # '\'script_type=down %s\'' % self.DOWN_SCRIPT
            ]

        args += [
            '--cert', eipconfig.get_client_cert_path(providerconfig),
            '--key', eipconfig.get_client_cert_path(providerconfig),
            '--ca', providerconfig.get_ca_cert_path()
        ]

        command = self.OSASCRIPT_BIN
        cmd_args = ["-e", self.OSX_ASADMIN % (' '.join(args),)]

        logger.debug("Running VPN with command:")
        logger.debug("%s %s" % (command, " ".join(cmd_args)))

        return [command] + cmd_args

    def get_vpn_env(self, providerconfig):
        """
        Returns a dictionary with the custom env for the platform.
        This is mainly used for setting LD_LIBRARY_PATH to the correct
        path when distributing a standalone client

        :param providerconfig: provider specific configuration
        :type providerconfig: ProviderConfig

        :rtype: dict
        """
        return {"DYLD_LIBRARY_PATH": os.path.join(
                providerconfig.get_path_prefix(),
                "..", "lib")}


class WindowsVPNLauncher(VPNLauncher):
    """
    VPN launcher for the Windows platform
    """

    OPENVPN_BIN = 'openvpn_leap.exe'

    def get_vpn_command(self, eipconfig=None, providerconfig=None,
                        socket_host=None, socket_port="9876"):
        """
        Returns the platform dependant vpn launching command. It will
        look for openvpn in the regular paths and algo in
        path_prefix/apps/eip/ (in case standalone is set)

        Might raise VPNException.

        :param eipconfig: eip configuration object
        :type eipconfig: EIPConfig
        :param providerconfig: provider specific configuration
        :type providerconfig: ProviderConfig
        :param socket_host: either socket path (unix) or socket IP
        :type socket_host: str
        :param socket_port: either string "unix" if it's a unix
        socket, or port otherwise
        :type socket_port: str

        :return: A VPN command ready to be launched
        :rtype: list
        """
        leap_assert(eipconfig, "We need an eip config")
        leap_assert_type(eipconfig, EIPConfig)
        leap_assert(providerconfig, "We need a provider config")
        leap_assert_type(providerconfig, ProviderConfig)
        leap_assert(socket_host, "We need a socket host!")
        leap_assert(socket_port, "We need a socket port!")
        leap_assert(socket_port != "unix",
                    "We cannot use unix sockets in windows!")

        openvpn_possibilities = which(
            self.OPENVPN_BIN,
            path_extension=os.path.join(providerconfig.get_path_prefix(),
                                        "..", "apps", "eip"))

        if len(openvpn_possibilities) == 0:
            raise OpenVPNNotFoundException()

        openvpn = openvpn_possibilities[0]
        args = []

        # TODO: handle verbosity

        gateway_ip = str(eipconfig.get_gateway_ip(0))

        logger.debug("Using gateway ip %s" % (gateway_ip,))

        args += [
            '--client',
            '--dev', 'tun',
            '--persist-tun',
            '--persist-key',
            '--remote', gateway_ip, '1194', 'udp',
            '--tls-client',
            '--remote-cert-tls',
            'server'
        ]

        openvpn_configuration = eipconfig.get_openvpn_configuration()
        # XXX sanitize this
        for key, value in openvpn_configuration.items():
            args += ['--%s' % (key,), value]

        args += [
            '--user', getpass.getuser(),
            #'--group', grp.getgrgid(os.getgroups()[-1]).gr_name
        ]

        args += [
            '--management-signal',
            '--management', socket_host, socket_port,
            '--script-security', '2'
        ]

        args += [
            '--cert', eipconfig.get_client_cert_path(providerconfig),
            '--key', eipconfig.get_client_cert_path(providerconfig),
            '--ca', providerconfig.get_ca_cert_path()
        ]

        logger.debug("Running VPN with command:")
        logger.debug("%s %s" % (openvpn, " ".join(args)))

        return [openvpn] + args

    def get_vpn_env(self, providerconfig):
        """
        Returns a dictionary with the custom env for the platform.
        This is mainly used for setting LD_LIBRARY_PATH to the correct
        path when distributing a standalone client

        :param providerconfig: provider specific configuration
        :type providerconfig: ProviderConfig

        :rtype: dict
        """
        return {}


if __name__ == "__main__":
    logger = logging.getLogger(name='leap')
    logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s '
        '- %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)

    try:
        abs_launcher = VPNLauncher()
    except Exception as e:
        assert isinstance(e, TypeError), "Something went wrong"
        print "Abstract Prefixer class is working as expected"

    vpnlauncher = get_platform_launcher()

    eipconfig = EIPConfig()
    if eipconfig.load("leap/providers/bitmask.net/eip-service.json"):
        provider = ProviderConfig()
        if provider.load("leap/providers/bitmask.net/provider.json"):
            vpnlauncher.get_vpn_command(eipconfig=eipconfig,
                                        providerconfig=provider,
                                        socket_host="/blah")
