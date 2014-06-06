# -*- coding: utf-8 -*-
# darwinvpnlauncher.py
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
Darwin VPN launcher implementation.
"""
import commands
import getpass
import logging
import os
import sys

from leap.bitmask.services.eip.vpnlauncher import VPNLauncher
from leap.bitmask.services.eip.vpnlauncher import VPNLauncherException
from leap.bitmask.util import get_path_prefix

logger = logging.getLogger(__name__)


class EIPNoTunKextLoaded(VPNLauncherException):
    pass


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
    OPENVPN_BIN_PATH = "%s/Contents/Resources/%s" % (INSTALL_PATH,
                                                     OPENVPN_BIN)

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

        cmd = "#!/bin/sh\n"
        cmd += "mkdir -p {0}\n".format(to)
        cmd += "cp '{0}'/* {1}\n".format(frompath, to)
        cmd += "chmod 744 {0}/*".format(to)

        return cmd

    @classmethod
    def is_kext_loaded(kls):
        """
        Checks if the needed kext is loaded before launching openvpn.

        :returns: True if kext is loaded, False otherwise.
        :rtype: bool
        """
        return bool(commands.getoutput('kextstat | grep "leap.tun"'))

    @classmethod
    def _get_icon_path(kls):
        """
        Returns the absolute path to the app icon.

        :rtype: str
        """
        resources_path = os.path.abspath(
            os.path.join(os.getcwd(), "../../Contents/Resources"))

        return os.path.join(resources_path, "bitmask.tiff")

    @classmethod
    def get_cocoasudo_ovpn_cmd(kls):
        """
        Returns a string with the cocoasudo command needed to run openvpn
        as admin with a nice password prompt. The actual command needs to be
        appended.

        :rtype: (str, list)
        """
        # TODO add translation support for this
        sudo_msg = ("Bitmask needs administrative privileges to run "
                    "Encrypted Internet.")
        iconpath = kls._get_icon_path()
        has_icon = os.path.isfile(iconpath)
        args = ["--icon=%s" % iconpath] if has_icon else []
        args.append("--prompt=%s" % (sudo_msg,))

        return kls.COCOASUDO, args

    @classmethod
    def get_cocoasudo_installmissing_cmd(kls):
        """
        Returns a string with the cocoasudo command needed to install missing
        files as admin with a nice password prompt. The actual command needs to
        be appended.

        :rtype: (str, list)
        """
        # TODO add translation support for this
        install_msg = ('"Bitmask needs administrative privileges to install '
                       'missing scripts and fix permissions."')
        iconpath = kls._get_icon_path()
        has_icon = os.path.isfile(iconpath)
        args = ["--icon=%s" % iconpath] if has_icon else []
        args.append("--prompt=%s" % (install_msg,))

        return kls.COCOASUDO, args

    @classmethod
    def get_vpn_command(kls, eipconfig, providerconfig, socket_host,
                        socket_port="unix", openvpn_verb=1):
        """
        Returns the OSX implementation for the vpn launching command.

        Might raise:
            EIPNoTunKextLoaded,
            OpenVPNNotFoundException,
            VPNLauncherException.

        :param eipconfig: eip configuration object
        :type eipconfig: EIPConfig
        :param providerconfig: provider specific configuration
        :type providerconfig: ProviderConfig
        :param socket_host: either socket path (unix) or socket IP
        :type socket_host: str
        :param socket_port: either string "unix" if it's a unix socket,
                            or port otherwise
        :type socket_port: str
        :param openvpn_verb: the openvpn verbosity wanted
        :type openvpn_verb: int

        :return: A VPN command ready to be launched.
        :rtype: list
        """
        if not kls.is_kext_loaded():
            raise EIPNoTunKextLoaded

        # we use `super` in order to send the class to use
        command = super(DarwinVPNLauncher, kls).get_vpn_command(
            eipconfig, providerconfig, socket_host, socket_port, openvpn_verb)

        cocoa, cargs = kls.get_cocoasudo_ovpn_cmd()
        cargs.extend(command)
        command = cargs
        command.insert(0, cocoa)

        command.extend(['--setenv', "LEAPUSER", getpass.getuser()])

        return command

    @classmethod
    def get_vpn_env(kls):
        """
        Returns a dictionary with the custom env for the platform.
        This is mainly used for setting LD_LIBRARY_PATH to the correct
        path when distributing a standalone client

        :rtype: dict
        """
        ld_library_path = os.path.join(get_path_prefix(), "..", "lib")
        ld_library_path.encode(sys.getfilesystemencoding())
        return {
            "DYLD_LIBRARY_PATH": ld_library_path
        }
