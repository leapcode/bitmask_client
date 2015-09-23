# -*- coding: utf-8 -*-
# emailfirewall.py
# Copyright (C) 2014 LEAP
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
Email firewall implementation.
"""

import os
import subprocess

from abc import ABCMeta, abstractmethod

from leap.bitmask.config import flags
from leap.bitmask.platform_init import IS_LINUX
from leap.bitmask.util import first, force_eval
from leap.bitmask.util.privilege_policies import LinuxPolicyChecker
from leap.common.check import leap_assert


def get_email_firewall():
    """
    Return the email firewall handler for the current platform.
    """
    # disable email firewall on a docker container so we can access from an
    # external MUA
    if os.environ.get("LEAP_DOCKERIZED"):
        return None

    if not (IS_LINUX):
        error_msg = "Email firewall not implemented for this platform."
        raise NotImplementedError(error_msg)

    firewall = None
    if IS_LINUX:
        firewall = LinuxEmailFirewall

    leap_assert(firewall is not None)

    return firewall()


class EmailFirewall(object):
    """
    Abstract email firwall class
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def start(self):
        """
        Start email firewall
        """
        return False

    @abstractmethod
    def stop(self):
        """
        Stop email firewall
        """
        return False


class EmailFirewallException(Exception):
    pass


class LinuxEmailFirewall(EmailFirewall):

    class BITMASK_ROOT(object):
        def __call__(self):
            return ("/usr/local/sbin/bitmask-root" if flags.STANDALONE else
                    "/usr/sbin/bitmask-root")

    def start(self):
        uid = str(os.getuid())
        return True if self._run(["start", uid]) is 0 else False

    def stop(self):
        return True if self._run(["stop"]) is 0 else False

    def _run(self, cmd):
        """
        Run an email firewall command with bitmask-root

        Might raise:
            NoPkexecAvailable,
            NoPolkitAuthAgentAvailable,

        :param cmd: command to send to bitmask-root fw-email
        :type cmd: [str]
        :returns: exit code of bitmask-root
        :rtype: int
        """
        command = []

        policyChecker = LinuxPolicyChecker()
        pkexec = policyChecker.maybe_pkexec()
        if pkexec:
            command.append(first(pkexec))

        command.append(force_eval(self.BITMASK_ROOT))
        command.append("fw-email")
        command += cmd

        # XXX: will be nice to use twisted ProcessProtocol instead of
        #      subprocess to avoid blocking until it finish
        return subprocess.call(command)
