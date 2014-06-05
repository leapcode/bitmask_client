# -*- coding: utf-8 -*-
# linuxvpnlauncher.py
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
Linux VPN launcher implementation.
"""
import commands
import logging
import os
import subprocess
import sys
import time

from leap.bitmask.config import flags
from leap.bitmask.util.privilege_policies import LinuxPolicyChecker
from leap.common.files import which
from leap.bitmask.services.eip.vpnlauncher import VPNLauncher
from leap.bitmask.services.eip.vpnlauncher import VPNLauncherException
from leap.bitmask.util import get_path_prefix
from leap.common.check import leap_assert
from leap.bitmask.util import first

logger = logging.getLogger(__name__)

COM = commands


class EIPNoPolkitAuthAgentAvailable(VPNLauncherException):
    pass


class EIPNoPkexecAvailable(VPNLauncherException):
    pass


def _is_pkexec_in_system():
    """
    Checks the existence of the pkexec binary in system.
    """
    pkexec_path = which('pkexec')
    if len(pkexec_path) == 0:
        return False
    return True


def _is_auth_agent_running():
    """
    Checks if a polkit daemon is running.

    :return: True if it's running, False if it's not.
    :rtype: boolean
    """
    # Note that gnome-shell does not uses a separate process for the
    # polkit-agent, it uses a polkit-agent within its own process so we can't
    # ps-grep a polkit process, we can ps-grep gnome-shell itself.

    # the [x] thing is to avoid grep match itself
    polkit_options = [
        'ps aux | grep "polkit-[g]nome-authentication-agent-1"',
        'ps aux | grep "polkit-[k]de-authentication-agent-1"',
        'ps aux | grep "polkit-[m]ate-authentication-agent-1"',
        'ps aux | grep "[l]xpolkit"',
        'ps aux | grep "[g]nome-shell"',
    ]
    is_running = [commands.getoutput(cmd) for cmd in polkit_options]

    return any(is_running)


def _try_to_launch_agent():
    """
    Tries to launch a polkit daemon.
    """
    env = None
    if flags.STANDALONE:
        env = {"PYTHONPATH": os.path.abspath('../../../../lib/')}
    try:
        # We need to quote the command because subprocess call
        # will do "sh -c 'foo'", so if we do not quoute it we'll end
        # up with a invocation to the python interpreter. And that
        # is bad.
        logger.debug("Trying to launch polkit agent")
        subprocess.call(["python -m leap.bitmask.util.polkit_agent"],
                        shell=True, env=env)
    except Exception as exc:
        logger.exception(exc)


SYSTEM_CONFIG = "/etc/leap"
leapfile = lambda f: "%s/%s" % (SYSTEM_CONFIG, f)


class LinuxVPNLauncher(VPNLauncher):
    PKEXEC_BIN = 'pkexec'
    BITMASK_ROOT = "/usr/sbin/bitmask-root"

    # We assume this is there by our openvpn dependency, and
    # we will put it there on the bundle too.
    if flags.STANDALONE:
        OPENVPN_BIN_PATH = "/usr/sbin/leap-openvpn"
    else:
        OPENVPN_BIN_PATH = "/usr/sbin/openvpn"

    POLKIT_PATH = LinuxPolicyChecker.get_polkit_path()

    if flags.STANDALONE:
        RESOLVCONF_BIN_PATH = "/usr/local/sbin/leap-resolvconf"
    else:
        # this only will work with debian/ubuntu distros.
        RESOLVCONF_BIN_PATH = "/sbin/resolvconf"

    # XXX openvpn binary TOO
    OTHER_FILES = (POLKIT_PATH, BITMASK_ROOT, OPENVPN_BIN_PATH,
                   RESOLVCONF_BIN_PATH)

    @classmethod
    def maybe_pkexec(kls):
        """
        Checks whether pkexec is available in the system, and
        returns the path if found.

        Might raise:
            EIPNoPkexecAvailable,
            EIPNoPolkitAuthAgentAvailable.

        :returns: a list of the paths where pkexec is to be found
        :rtype: list
        """
        if _is_pkexec_in_system():
            if not _is_auth_agent_running():
                _try_to_launch_agent()
                time.sleep(2)
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
    def get_vpn_command(kls, eipconfig, providerconfig, socket_host,
                        socket_port="unix", openvpn_verb=1):
        """
        Returns the Linux implementation for the vpn launching command.

        Might raise:
            EIPNoPkexecAvailable,
            EIPNoPolkitAuthAgentAvailable,
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
        # we use `super` in order to send the class to use
        command = super(LinuxVPNLauncher, kls).get_vpn_command(
            eipconfig, providerconfig, socket_host, socket_port, openvpn_verb)

        command.insert(0, kls.BITMASK_ROOT)
        command.insert(1, "openvpn")
        command.insert(2, "start")

        pkexec = kls.maybe_pkexec()
        if pkexec:
            command.insert(0, first(pkexec))

        return command

    @classmethod
    def cmd_for_missing_scripts(kls, frompath):
        """
        Returns a sh script that can copy the missing files.

        :param frompath: The path where the helper files live
        :type frompath: str

        :rtype: str
        """
        # no system config for now
        # sys_config = kls.SYSTEM_CONFIG
        (polkit_file, openvpn_bin_file,
         bitmask_root_file, resolvconf_bin_file) = map(
            lambda p: os.path.split(p)[-1],
            (kls.POLKIT_PATH, kls.OPENVPN_BIN_PATH,
             kls.BITMASK_ROOT, kls.RESOLVCONF_BIN_PATH))

        cmd = '#!/bin/sh\n'
        cmd += 'mkdir -p /usr/local/sbin\n'

        cmd += 'cp "%s" "%s"\n' % (os.path.join(frompath, polkit_file),
                                   kls.POLKIT_PATH)
        cmd += 'chmod 644 "%s"\n' % (kls.POLKIT_PATH, )

        cmd += 'cp "%s" "%s"\n' % (os.path.join(frompath, bitmask_root_file),
                                   kls.BITMASK_ROOT)
        cmd += 'chmod 744 "%s"\n' % (kls.BITMASK_ROOT, )

        if flags.STANDALONE:
            cmd += 'cp "%s" "%s"\n' % (
                os.path.join(frompath, openvpn_bin_file),
                kls.OPENVPN_BIN_PATH)
            cmd += 'chmod 744 "%s"\n' % (kls.POLKIT_PATH, )

            cmd += 'cp "%s" "%s"\n' % (
                os.path.join(frompath, resolvconf_bin_file),
                kls.RESOLVCONF_BIN_PATH)
            cmd += 'chmod 744 "%s"\n' % (kls.POLKIT_PATH, )
        return cmd

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
            "LD_LIBRARY_PATH": ld_library_path
        }
