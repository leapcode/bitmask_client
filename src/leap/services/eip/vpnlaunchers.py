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
import os
import platform
import logging
import commands
import getpass
import grp

from abc import ABCMeta, abstractmethod

from leap.config.providerconfig import ProviderConfig
from leap.services.eip.eipconfig import EIPConfig
from leap.util.check import leap_assert, leap_assert_type

logger = logging.getLogger(__name__)


class VPNLauncherException(Exception):
    pass


class VPNLauncher:
    """
    Abstract launcher class
    """

    __metaclass__ = ABCMeta

    # TODO: document parameters
    @abstractmethod
    def get_vpn_command(self, eipconfig=None, providerconfig=None,
                        socket_host=None, socket_port=None):
        """
        Returns the platform dependant vpn launching command

        @param eipconfig: eip configuration object
        @type eipconfig: EIPConfig
        @param providerconfig: provider specific configuration
        @type providerconfig: ProviderConfig
        @param socket_host: either socket path (unix) or socket IP
        @type socket_host: str
        @param socket_port: either string "unix" if it's a unix
        socket, or port otherwise
        @type socket_port: str

        @return: A VPN command ready to be launched
        @rtype: list
        """
        return []


def get_platform_launcher():
    launcher = globals()[platform.system() + "VPNLauncher"]
    leap_assert(launcher, "Unimplemented platform launcher: %s" %
                (platform.system(),))
    return launcher()


# Twisted implementation of which
def which(name, flags=os.X_OK):
    """
    Search PATH for executable files with the given name.

    On newer versions of MS-Windows, the PATHEXT environment variable will be
    set to the list of file extensions for files considered executable. This
    will normally include things like ".EXE". This fuction will also find files
    with the given name ending with any of these extensions.

    On MS-Windows the only flag that has any meaning is os.F_OK. Any other
    flags will be ignored.

    @type name: C{str}
    @param name: The name for which to search.

    @type flags: C{int}
    @param flags: Arguments to L{os.access}.

    @rtype: C{list}
    @param: A list of the full paths to files found, in the
    order in which they were found.
    """

    # TODO: make sure sbin is in path

    result = []
    exts = filter(None, os.environ.get('PATHEXT', '').split(os.pathsep))
    path = os.environ.get('PATH', None)
    if path is None:
        return []
    for p in os.environ.get('PATH', '').split(os.pathsep):
        p = os.path.join(p, name)
        if os.access(p, flags):
            result.append(p)
        for e in exts:
            pext = p + e
            if os.access(pext, flags):
                result.append(pext)
    return result


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
        logger.warning("Could not find up/down scripts. " +
                       "Might produce DNS leaks.")
    return is_file


def _is_auth_agent_running():
    return bool(
        commands.getoutput(
            'ps aux | grep polkit-[g]nome-authentication-agent-1'))


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
        Returns the platform dependant vpn launching command

        Might raise VPNException.

        @param eipconfig: eip configuration object
        @type eipconfig: EIPConfig
        @param providerconfig: provider specific configuration
        @type providerconfig: ProviderConfig
        @param socket_host: either socket path (unix) or socket IP
        @type socket_host: str
        @param socket_port: either string "unix" if it's a unix
        socket, or port otherwise
        @type socket_port: str

        @return: A VPN command ready to be launched
        @rtype: list
        """
        leap_assert(eipconfig, "We need an eip config")
        leap_assert_type(eipconfig, EIPConfig)
        leap_assert(providerconfig, "We need a provider config")
        leap_assert_type(providerconfig, ProviderConfig)
        leap_assert(socket_host, "We need a socket host!")
        leap_assert(socket_port, "We need a socket port!")

        openvpn_possibilities = which(self.OPENVPN_BIN)
        if len(openvpn_possibilities) == 0:
            raise VPNLauncherException("We couldn't find openvpn")

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
        else:
            logger.warning("System has no pkexec")

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
