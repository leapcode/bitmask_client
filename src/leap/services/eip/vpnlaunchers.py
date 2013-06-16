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
from functools import partial

from leap.common.check import leap_assert, leap_assert_type
from leap.common.files import which
from leap.config.providerconfig import ProviderConfig
from leap.services.eip.eipconfig import EIPConfig, VPNGatewaySelector
from leap.util import first

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

    UPDOWN_FILES = None
    OTHER_FILES = None

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

    @classmethod
    def missing_updown_scripts(kls):
        """
        Returns what updown scripts are missing.
        :rtype: list
        """
        leap_assert(kls.UPDOWN_FILES is not None,
                    "Need to define UPDOWN_FILES for this particular "
                    "auncher before calling this method")
        file_exist = partial(_has_updown_scripts, warn=False)
        zipped = zip(kls.UPDOWN_FILES, map(file_exist, kls.UPDOWN_FILES))
        missing = filter(lambda (path, exists): exists is False, zipped)
        return [path for path, exists in missing]

    @classmethod
    def missing_other_files(kls):
        """
        Returns what other important files are missing during startup.
        Same as missing_updown_scripts but does not check for exec bit.
        :rtype: list
        """
        leap_assert(kls.UPDOWN_FILES is not None,
                    "Need to define OTHER_FILES for this particular "
                    "auncher before calling this method")
        file_exist = partial(_has_other_files, warn=False)
        zipped = zip(kls.OTHER_FILES, map(file_exist, kls.OTHER_FILES))
        missing = filter(lambda (path, exists): exists is False, zipped)
        return [path for path, exists in missing]


def get_platform_launcher():
    launcher = globals()[platform.system() + "VPNLauncher"]
    leap_assert(launcher, "Unimplemented platform launcher: %s" %
                (platform.system(),))
    return launcher()


def _is_pkexec_in_system():
    """
    Checks the existence of the pkexec binary in system.
    """
    pkexec_path = which('pkexec')
    if len(pkexec_path) == 0:
        return False
    return True


def _has_updown_scripts(path, warn=True):
    """
    Checks the existence of the up/down scripts and its
    exec bit if applicable.

    :param path: the path to be checked
    :type path: str

    :param warn: whether we should log the absence
    :type warn: bool

    :rtype: bool
    """
    is_file = os.path.isfile(path)
    if warn and not is_file:
        logger.error("Could not find up/down script %s. "
                     "Might produce DNS leaks." % (path,))

    # XXX check if applies in win
    is_exe = os.access(path, os.X_OK)
    if warn and not is_exe:
        logger.error("Up/down script %s is not executable. "
                     "Might produce DNS leaks." % (path,))
    return is_file and is_exe


def _has_other_files(path, warn=True):
    """
    Checks the existence of other important files.

    :param path: the path to be checked
    :type path: str

    :param warn: whether we should log the absence
    :type warn: bool

    :rtype: bool
    """
    is_file = os.path.isfile(path)
    if warn and not is_file:
        logger.warning("Could not find file during checks: %s. " % (
            path,))
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
    SYSTEM_CONFIG = "/etc/leap"
    UP_DOWN_FILE = "resolv-update"
    UP_DOWN_PATH = "%s/%s" % (SYSTEM_CONFIG, UP_DOWN_FILE)

    # We assume this is there by our openvpn dependency, and
    # we will put it there on the bundle too.
    # TODO adapt to the bundle path.
    OPENVPN_DOWN_ROOT = "/usr/lib/openvpn/openvpn-plugin-down-root.so"

    POLKIT_BASE = "/usr/share/polkit-1/actions"
    POLKIT_FILE = "net.openvpn.gui.leap.policy"
    POLKIT_PATH = "%s/%s" % (POLKIT_BASE, POLKIT_FILE)

    UPDOWN_FILES = (UP_DOWN_PATH,)
    OTHER_FILES = (POLKIT_PATH,)

    @classmethod
    def cmd_for_missing_scripts(kls, frompath):
        """
        Returns a command that can copy the missing scripts.
        :rtype: str
        """
        to = kls.SYSTEM_CONFIG
        cmd = "#!/bin/sh\nset -e\nmkdir -p %s\ncp %s/%s %s\ncp %s/%s %s" % (
            to,
            frompath, kls.UP_DOWN_FILE, to,
            frompath, kls.POLKIT_FILE, kls.POLKIT_PATH)
        return cmd

    @classmethod
    def maybe_pkexec(kls):
        """
        Checks whether pkexec is available in the system, and
        returns the path if found.

        Might raise EIPNoPkexecAvailable or EIPNoPolkitAuthAgentAvailable

        :returns: a list of the paths where pkexec is to be found
        :rtype: list
        """
        if _is_pkexec_in_system():
            if _is_auth_agent_running():
                pkexec_possibilities = which(kls.PKEXEC_BIN)
                leap_assert(len(pkexec_possibilities) > 0,
                            "We couldn't find pkexec")
                return pkexec_possibilities
            else:
                logger.warning("No polkit auth agent found. pkexec " +
                               "will use its own auth agent.")
                raise EIPNoPolkitAuthAgentAvailable()
        else:
            logger.warning("System has no pkexec")
            raise EIPNoPkexecAvailable()

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

        openvpn_possibilities = which(self.OPENVPN_BIN, **kwargs)

        if len(openvpn_possibilities) == 0:
            raise OpenVPNNotFoundException()

        openvpn = first(openvpn_possibilities)
        args = []

        pkexec = self.maybe_pkexec()
        if pkexec:
            args.append(openvpn)
            openvpn = first(pkexec)

        # TODO: handle verbosity

        gateway_selector = VPNGatewaySelector(eipconfig)
        gateway_ip = gateway_selector.get_best_gateway_ip()

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

        if _has_updown_scripts(self.UP_DOWN_PATH):
            args += [
                '--up', self.UP_DOWN_PATH,
                '--down', self.UP_DOWN_PATH,
                '--plugin', self.OPENVPN_DOWN_ROOT,
                '\'script_type=down %s\'' % self.UP_DOWN_PATH
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

    INSTALL_PATH = "/Applications/LEAP\ Client.app"
    # OPENVPN_BIN = "/%s/Contents/Resources/openvpn.leap" % (
    #   self.INSTALL_PATH,)
    OPENVPN_BIN = 'openvpn.leap'
    OPENVPN_PATH = "%s/Contents/Resources/openvpn" % (INSTALL_PATH,)

    UP_SCRIPT = "%s/client.up.sh" % (OPENVPN_PATH,)
    DOWN_SCRIPT = "%s/client.down.sh" % (OPENVPN_PATH,)
    OPENVPN_DOWN_PLUGIN = '%s/openvpn-down-root.so' % (OPENVPN_PATH,)

    UPDOWN_FILES = (UP_SCRIPT, DOWN_SCRIPT, OPENVPN_DOWN_PLUGIN)

    @classmethod
    def cmd_for_missing_scripts(kls, frompath):
        """
        Returns a command that can copy the missing scripts.
        :rtype: str
        """
        to = kls.OPENVPN_PATH
        cmd = "#!/bin/sh\nmkdir -p %s\ncp \"%s/\"* %s" % (to, frompath, to)
        #return kls.OSX_ASADMIN % cmd
        return cmd

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

        openvpn = first(openvpn_possibilities)
        args = [openvpn]

        # TODO: handle verbosity

        gateway_selector = VPNGatewaySelector(eipconfig)
        gateway_ip = gateway_selector.get_best_gateway_ip()

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

        user = getpass.getuser()
        args += [
            '--user', user,
            '--group', grp.getgrgid(os.getgroups()[-1]).gr_name
        ]

        if socket_port == "unix":
            args += [
                '--management-client-user', user
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
                '--down', self.DOWN_SCRIPT]

            # should have the down script too
            if _has_updown_scripts(self.OPENVPN_DOWN_PLUGIN):
                args += [
                    '--plugin', self.OPENVPN_DOWN_PLUGIN,
                    '\'%s\'' % self.DOWN_SCRIPT
                ]

        # we set user to be passed to the up/down scripts
        args += [
            '--setenv', "LEAPUSER", "%s" % (user,)]

        args += [
            '--cert', eipconfig.get_client_cert_path(providerconfig),
            '--key', eipconfig.get_client_cert_path(providerconfig),
            '--ca', providerconfig.get_ca_cert_path()
        ]

        # We are using osascript until we can write a proper wrapper
        # for privilege escalation.

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

    # XXX UPDOWN_FILES ... we do not have updown files defined yet!

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

        openvpn = first(openvpn_possibilities)
        args = []

        # TODO: handle verbosity

        gateway_selector = VPNGatewaySelector(eipconfig)
        gateway_ip = gateway_selector.get_best_gateway_ip()

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
