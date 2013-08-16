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
import subprocess
import stat
try:
    import grp
except ImportError:
    pass  # ignore, probably windows

from abc import ABCMeta, abstractmethod
from functools import partial

from leap.bitmask.config.providerconfig import ProviderConfig
from leap.bitmask.services.eip.eipconfig import EIPConfig, VPNGatewaySelector
from leap.bitmask.util import first
from leap.bitmask.util.privilege_policies import LinuxPolicyChecker
from leap.bitmask.util import privilege_policies
from leap.common.check import leap_assert, leap_assert_type
from leap.common.files import which

logger = logging.getLogger(__name__)


class VPNLauncherException(Exception):
    pass


class OpenVPNNotFoundException(VPNLauncherException):
    pass


class EIPNoPolkitAuthAgentAvailable(VPNLauncherException):
    pass


class EIPNoPkexecAvailable(VPNLauncherException):
    pass


class EIPNoTunKextLoaded(VPNLauncherException):
    pass


class VPNLauncher(object):
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
    is_exe = False
    try:
        is_exe = (stat.S_IXUSR & os.stat(path)[stat.ST_MODE] != 0)
    except OSError as e:
        logger.warn("%s" % (e,))
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
    ps = 'ps aux | grep polkit-%s-authentication-agent-1'
    opts = (ps % case for case in ['[g]nome', '[k]de'])
    is_running = map(lambda l: commands.getoutput(l), opts)
    return any(is_running)


def _try_to_launch_agent():
    """
    Tries to launch a polkit daemon.
    """
    opts = [
        "/usr/lib/policykit-1-gnome/polkit-gnome-authentication-agent-1",
        # XXX add kde thing here
    ]
    for cmd in opts:
        try:
            subprocess.Popen([cmd], shell=True)
        except:
            pass


class LinuxVPNLauncher(VPNLauncher):
    """
    VPN launcher for the Linux platform
    """

    PKEXEC_BIN = 'pkexec'
    OPENVPN_BIN = 'openvpn'
    OPENVPN_BIN_PATH = os.path.join(
        ProviderConfig().get_path_prefix(),
        "..", "apps", "eip", OPENVPN_BIN)

    SYSTEM_CONFIG = "/etc/leap"
    UP_DOWN_FILE = "resolv-update"
    UP_DOWN_PATH = "%s/%s" % (SYSTEM_CONFIG, UP_DOWN_FILE)

    # We assume this is there by our openvpn dependency, and
    # we will put it there on the bundle too.
    # TODO adapt to the bundle path.
    OPENVPN_DOWN_ROOT_BASE = "/usr/lib/openvpn/"
    OPENVPN_DOWN_ROOT_FILE = "openvpn-plugin-down-root.so"
    OPENVPN_DOWN_ROOT_PATH = "%s/%s" % (
        OPENVPN_DOWN_ROOT_BASE,
        OPENVPN_DOWN_ROOT_FILE)

    UPDOWN_FILES = (UP_DOWN_PATH,)
    POLKIT_PATH = LinuxPolicyChecker.get_polkit_path()
    OTHER_FILES = (POLKIT_PATH, )

    def missing_other_files(self):
        """
        'Extend' the VPNLauncher's missing_other_files to check if the polkit
        files is outdated. If the polkit file that is in OTHER_FILES exists but
        is not up to date, it is added to the missing list.

        :returns: a list of missing files
        :rtype: list of str
        """
        missing = VPNLauncher.missing_other_files.im_func(self)
        polkit_file = LinuxPolicyChecker.get_polkit_path()
        if polkit_file not in missing:
            if privilege_policies.is_policy_outdated(self.OPENVPN_BIN_PATH):
                missing.append(polkit_file)

        return missing

    @classmethod
    def cmd_for_missing_scripts(kls, frompath, pol_file):
        """
        Returns a sh script that can copy the missing files.

        :param frompath: The path where the up/down scripts live
        :type frompath: str
        :param pol_file: The path where the dynamically generated
                         policy file lives
        :type pol_file: str

        :rtype: str
        """
        to = kls.SYSTEM_CONFIG

        cmd = '#!/bin/sh\n'
        cmd += 'mkdir -p "%s"\n' % (to, )
        cmd += 'cp "%s/%s" "%s"\n' % (frompath, kls.UP_DOWN_FILE, to)
        cmd += 'cp "%s" "%s"\n' % (pol_file, kls.POLKIT_PATH)
        cmd += 'chmod 644 "%s"\n' % (kls.POLKIT_PATH, )

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
            if not _is_auth_agent_running():
                _try_to_launch_agent()
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

    @classmethod
    def maybe_down_plugin(kls):
        """
        Returns the path of the openvpn down-root-plugin, searching first
        in the relative path for the standalone bundle, and then in the system
        path where the debian package puts it.

        :returns: the path where the plugin was found, or None
        :rtype: str or None
        """
        cwd = os.getcwd()
        rel_path_in_bundle = os.path.join(
            'apps', 'eip', 'files', kls.OPENVPN_DOWN_ROOT_FILE)
        abs_path_in_bundle = os.path.join(cwd, rel_path_in_bundle)
        if os.path.isfile(abs_path_in_bundle):
            return abs_path_in_bundle
        abs_path_in_system = kls.OPENVPN_DOWN_ROOT_FILE
        if os.path.isfile(abs_path_in_system):
            return abs_path_in_system

        logger.warning("We could not find the down-root-plugin, so no updown "
                       "scripts will be run. DNS leaks are likely!")
        return None

    def get_vpn_command(self, eipconfig=None, providerconfig=None,
                        socket_host=None, socket_port="unix", openvpn_verb=1):
        """
        Returns the platform dependant vpn launching command. It will
        look for openvpn in the regular paths and algo in
        path_prefix/apps/eip/ (in case standalone is set)

        Might raise:
            VPNLauncherException,
            OpenVPNNotFoundException.

        :param eipconfig: eip configuration object
        :type eipconfig: EIPConfig

        :param providerconfig: provider specific configuration
        :type providerconfig: ProviderConfig

        :param socket_host: either socket path (unix) or socket IP
        :type socket_host: str

        :param socket_port: either string "unix" if it's a unix
                            socket, or port otherwise
        :type socket_port: str

        :param openvpn_verb: openvpn verbosity wanted
        :type openvpn_verb: int

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

        args += [
            '--setenv', "LEAPOPENVPN", "1"
        ]

        if openvpn_verb is not None:
            args += ['--verb', '%d' % (openvpn_verb,)]

        gateway_selector = VPNGatewaySelector(eipconfig)
        gateways = gateway_selector.get_gateways()

        if not gateways:
            logger.error('No gateway was found!')
            raise VPNLauncherException(self.tr('No gateway was found!'))

        logger.debug("Using gateways ips: {}".format(', '.join(gateways)))

        for gw in gateways:
            args += ['--remote', gw, '1194', 'udp']

        args += [
            '--client',
            '--dev', 'tun',
            ##############################################################
            # persist-tun makes ping-restart fail because it leaves a
            # broken routing table
            ##############################################################
            # '--persist-tun',
            '--persist-key',
            '--tls-client',
            '--remote-cert-tls',
            'server'
        ]

        openvpn_configuration = eipconfig.get_openvpn_configuration()

        for key, value in openvpn_configuration.items():
            args += ['--%s' % (key,), value]

        ##############################################################
        # The down-root plugin fails in some situations, so we don't
        # drop privs for the time being
        ##############################################################
        # args += [
        #     '--user', getpass.getuser(),
        #     '--group', grp.getgrgid(os.getgroups()[-1]).gr_name
        # ]

        if socket_port == "unix":  # that's always the case for linux
            args += [
                '--management-client-user', getpass.getuser()
            ]

        args += [
            '--management-signal',
            '--management', socket_host, socket_port,
            '--script-security', '2'
        ]

        plugin_path = self.maybe_down_plugin()
        # If we do not have the down plugin neither in the bundle
        # nor in the system, we do not do updown scripts. The alternative
        # is leaving the user without the ability to restore dns and routes
        # to its original state.

        if plugin_path and _has_updown_scripts(self.UP_DOWN_PATH):
            args += [
                '--up', self.UP_DOWN_PATH,
                '--down', self.UP_DOWN_PATH,
                ##############################################################
                # For the time being we are disabling the usage of the
                # down-root plugin, because it doesn't quite work as
                # expected (i.e. it doesn't run route -del as root
                # when finishing, so it fails to properly
                # restart/quit)
                ##############################################################
                # '--plugin', plugin_path,
                # '\'script_type=down %s\'' % self.UP_DOWN_PATH
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

    COCOASUDO = "cocoasudo"
    # XXX need the good old magic translate for these strings
    # (look for magic in 0.2.0 release)
    SUDO_MSG = ("Bitmask needs administrative privileges to run "
                "Encrypted Internet.")
    INSTALL_MSG = ("\"Bitmask needs administrative privileges to install "
                   "missing scripts and fix permissions.\"")

    INSTALL_PATH = os.path.realpath(os.getcwd() + "/../../")
    INSTALL_PATH_ESCAPED = os.path.realpath(os.getcwd() + "/../../")
    OPENVPN_BIN = 'openvpn.leap'
    OPENVPN_PATH = "%s/Contents/Resources/openvpn" % (INSTALL_PATH,)
    OPENVPN_PATH_ESCAPED = "%s/Contents/Resources/openvpn" % (
        INSTALL_PATH_ESCAPED,)

    UP_SCRIPT = "%s/client.up.sh" % (OPENVPN_PATH,)
    DOWN_SCRIPT = "%s/client.down.sh" % (OPENVPN_PATH,)
    OPENVPN_DOWN_PLUGIN = '%s/openvpn-down-root.so' % (OPENVPN_PATH,)

    UPDOWN_FILES = (UP_SCRIPT, DOWN_SCRIPT, OPENVPN_DOWN_PLUGIN)
    OTHER_FILES = []

    @classmethod
    def cmd_for_missing_scripts(kls, frompath):
        """
        Returns a command that can copy the missing scripts.
        :rtype: str
        """
        to = kls.OPENVPN_PATH_ESCAPED
        cmd = "#!/bin/sh\nmkdir -p %s\ncp \"%s/\"* %s\nchmod 744 %s/*" % (
            to, frompath, to, to)
        return cmd

    @classmethod
    def maybe_kextloaded(kls):
        """
        Checks if the needed kext is loaded before launching openvpn.
        """
        return bool(commands.getoutput('kextstat | grep "leap.tun"'))

    def _get_resource_path(self):
        """
        Returns the absolute path to the app resources directory

        :rtype: str
        """
        return os.path.abspath(
            os.path.join(
                os.getcwd(),
                "../../Contents/Resources"))

    def _get_icon_path(self):
        """
        Returns the absolute path to the app icon

        :rtype: str
        """
        return os.path.join(self._get_resource_path(),
                            "leap-client.tiff")

    def get_cocoasudo_ovpn_cmd(self):
        """
        Returns a string with the cocoasudo command needed to run openvpn
        as admin with a nice password prompt. The actual command needs to be
        appended.

        :rtype: (str, list)
        """
        iconpath = self._get_icon_path()
        has_icon = os.path.isfile(iconpath)
        args = ["--icon=%s" % iconpath] if has_icon else []
        args.append("--prompt=%s" % (self.SUDO_MSG,))

        return self.COCOASUDO, args

    def get_cocoasudo_installmissing_cmd(self):
        """
        Returns a string with the cocoasudo command needed to install missing
        files as admin with a nice password prompt. The actual command needs to
        be appended.

        :rtype: (str, list)
        """
        iconpath = self._get_icon_path()
        has_icon = os.path.isfile(iconpath)
        args = ["--icon=%s" % iconpath] if has_icon else []
        args.append("--prompt=%s" % (self.INSTALL_MSG,))

        return self.COCOASUDO, args

    def get_vpn_command(self, eipconfig=None, providerconfig=None,
                        socket_host=None, socket_port="unix", openvpn_verb=1):
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

        :param openvpn_verb: openvpn verbosity wanted
        :type openvpn_verb: int

        :return: A VPN command ready to be launched
        :rtype: list
        """
        leap_assert(eipconfig, "We need an eip config")
        leap_assert_type(eipconfig, EIPConfig)
        leap_assert(providerconfig, "We need a provider config")
        leap_assert_type(providerconfig, ProviderConfig)
        leap_assert(socket_host, "We need a socket host!")
        leap_assert(socket_port, "We need a socket port!")

        if not self.maybe_kextloaded():
            raise EIPNoTunKextLoaded

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

        args += [
            '--setenv', "LEAPOPENVPN", "1"
        ]

        if openvpn_verb is not None:
            args += ['--verb', '%d' % (openvpn_verb,)]

        gateway_selector = VPNGatewaySelector(eipconfig)
        gateways = gateway_selector.get_gateways()

        logger.debug("Using gateways ips: {gw}".format(
            gw=', '.join(gateways)))

        for gw in gateways:
            args += ['--remote', gw, '1194', 'udp']

        args += [
            '--client',
            '--dev', 'tun',
            ##############################################################
            # persist-tun makes ping-restart fail because it leaves a
            # broken routing table
            ##############################################################
            # '--persist-tun',
            '--persist-key',
            '--tls-client',
            '--remote-cert-tls',
            'server'
        ]

        openvpn_configuration = eipconfig.get_openvpn_configuration()
        for key, value in openvpn_configuration.items():
            args += ['--%s' % (key,), value]

        user = getpass.getuser()

        ##############################################################
        # The down-root plugin fails in some situations, so we don't
        # drop privs for the time being
        ##############################################################
        # args += [
        #     '--user', user,
        #     '--group', grp.getgrgid(os.getgroups()[-1]).gr_name
        # ]

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
                '--up', '\"%s\"' % (self.UP_SCRIPT,),
            ]

        if _has_updown_scripts(self.DOWN_SCRIPT):
            args += [
                '--down', '\"%s\"' % (self.DOWN_SCRIPT,)
            ]

            # should have the down script too
            if _has_updown_scripts(self.OPENVPN_DOWN_PLUGIN):
                args += [
                    ###########################################################
                    # For the time being we are disabling the usage of the
                    # down-root plugin, because it doesn't quite work as
                    # expected (i.e. it doesn't run route -del as root
                    # when finishing, so it fails to properly
                    # restart/quit)
                    ###########################################################
                    # '--plugin', self.OPENVPN_DOWN_PLUGIN,
                    # '\'%s\'' % self.DOWN_SCRIPT
                ]

        # we set user to be passed to the up/down scripts
        args += [
            '--setenv', "LEAPUSER", "%s" % (user,)]

        args += [
            '--cert', eipconfig.get_client_cert_path(providerconfig),
            '--key', eipconfig.get_client_cert_path(providerconfig),
            '--ca', providerconfig.get_ca_cert_path()
        ]

        command, cargs = self.get_cocoasudo_ovpn_cmd()
        cmd_args = cargs + args

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
    # (and maybe we won't)

    def get_vpn_command(self, eipconfig=None, providerconfig=None,
                        socket_host=None, socket_port="9876", openvpn_verb=1):
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

        :param openvpn_verb: the openvpn verbosity wanted
        :type openvpn_verb: int

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

        args += [
            '--setenv', "LEAPOPENVPN", "1"
        ]

        if openvpn_verb is not None:
            args += ['--verb', '%d' % (openvpn_verb,)]

        gateway_selector = VPNGatewaySelector(eipconfig)
        gateways = gateway_selector.get_gateways()

        logger.debug("Using gateways ips: {}".format(', '.join(gateways)))

        for gw in gateways:
            args += ['--remote', gw, '1194', 'udp']

        args += [
            '--client',
            '--dev', 'tun',
            ##############################################################
            # persist-tun makes ping-restart fail because it leaves a
            # broken routing table
            ##############################################################
            # '--persist-tun',
            '--persist-key',
            '--tls-client',
            # We make it log to a file because we cannot attach to the
            # openvpn process' stdout since it's a process with more
            # privileges than we are
            '--log-append', 'eip.log',
            '--remote-cert-tls',
            'server'
        ]

        openvpn_configuration = eipconfig.get_openvpn_configuration()
        for key, value in openvpn_configuration.items():
            args += ['--%s' % (key,), value]

        ##############################################################
        # The down-root plugin fails in some situations, so we don't
        # drop privs for the time being
        ##############################################################
        # args += [
        #     '--user', getpass.getuser(),
        #     #'--group', grp.getgrgid(os.getgroups()[-1]).gr_name
        # ]

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
    eipconfig.set_api_version('1')
    if eipconfig.load("leap/providers/bitmask.net/eip-service.json"):
        provider = ProviderConfig()
        if provider.load("leap/providers/bitmask.net/provider.json"):
            vpnlauncher.get_vpn_command(eipconfig=eipconfig,
                                        providerconfig=provider,
                                        socket_host="/blah")
