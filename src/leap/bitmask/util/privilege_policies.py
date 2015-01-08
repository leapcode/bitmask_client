# -*- coding: utf-8 -*-
# privilege_policies.py
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
Helpers to determine if the needed policies for privilege escalation
are operative under this client run.
"""
import commands
import logging
import os
import subprocess
import platform
import time

from abc import ABCMeta, abstractmethod

from leap.bitmask.config import flags
from leap.common.check import leap_assert
from leap.common.files import which

logger = logging.getLogger(__name__)


class NoPolkitAuthAgentAvailable(Exception):
    pass


class NoPkexecAvailable(Exception):
    pass


def is_missing_policy_permissions():
    """
    Returns True if we do not have implemented a policy checker for this
    platform, or if the policy checker exists but it cannot find the
    appropriate policy mechanisms in place.

    :rtype: bool
    """
    _system = platform.system()
    platform_checker = _system + "PolicyChecker"
    policy_checker = globals().get(platform_checker, None)
    if not policy_checker:
        # it is true that we miss permission to escalate
        # privileges without asking for password each time.
        logger.debug("we could not find a policy checker implementation "
                     "for %s" % (_system,))
        return True
    return policy_checker().is_missing_policy_permissions()


class PolicyChecker:
    """
    Abstract PolicyChecker class
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def is_missing_policy_permissions(self):
        """
        Returns True if we could not find any policy mechanisms that
        are defined to be in used for this particular platform.

        :rtype: bool
        """
        return True


class LinuxPolicyChecker(PolicyChecker):
    """
    PolicyChecker for Linux
    """
    LINUX_POLKIT_FILE = ("/usr/share/polkit-1/actions/"
                         "se.leap.bitmask.policy")
    LINUX_POLKIT_FILE_BUNDLE = ("/usr/share/polkit-1/actions/"
                                "se.leap.bitmask.bundle.policy")
    PKEXEC_BIN = 'pkexec'

    @classmethod
    def get_polkit_path(self):
        """
        Returns the polkit file path.

        :rtype: str
        """
        return (self.LINUX_POLKIT_FILE_BUNDLE if flags.STANDALONE
                else self.LINUX_POLKIT_FILE)

    def is_missing_policy_permissions(self):
        # FIXME this name is quite confusing, it does not have anything to do
        # with file permissions.
        """
        Returns True if we could not find the appropriate policykit file
        in place

        :rtype: bool
        """
        path = self.get_polkit_path()
        return not os.path.isfile(path)

    @classmethod
    def maybe_pkexec(self):
        """
        Checks whether pkexec is available in the system, and
        returns the path if found.

        Might raise:
            NoPkexecAvailable,
            NoPolkitAuthAgentAvailable.

        :returns: a list of the paths where pkexec is to be found
        :rtype: list
        """
        if self._is_pkexec_in_system():
            if not self.is_up():
                self.launch()
                time.sleep(2)
            if self.is_up():
                pkexec_possibilities = which(self.PKEXEC_BIN)
                leap_assert(len(pkexec_possibilities) > 0,
                            "We couldn't find pkexec")
                return pkexec_possibilities
            else:
                logger.warning("No polkit auth agent found. pkexec " +
                               "will use its own auth agent.")
                raise NoPolkitAuthAgentAvailable()
        else:
            logger.warning("System has no pkexec")
            raise NoPkexecAvailable()

    @classmethod
    def launch(self):
        """
        Tries to launch policykit
        """
        env = None
        if flags.STANDALONE:
            # This allows us to send to subprocess the environment configs that
            # works for the standalone bundle (like the PYTHONPATH)
            env = dict(os.environ)
            # The LD_LIBRARY_PATH is set on the launcher but not forwarded to
            # subprocess unless we do so explicitly.
            env["LD_LIBRARY_PATH"] = os.path.abspath("./lib/")
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

    @classmethod
    def is_up(self):
        """
        Checks if a polkit daemon is running.

        :return: True if it's running, False if it's not.
        :rtype: boolean
        """
        # Note that gnome-shell does not uses a separate process for the
        # polkit-agent, it uses a polkit-agent within its own process so we
        # can't ps-grep a polkit process, we can ps-grep gnome-shell itself.

        # the [x] thing is to avoid grep match itself
        polkit_options = [
            'ps aux | grep "polkit-[g]nome-authentication-agent-1"',
            'ps aux | grep "polkit-[k]de-authentication-agent-1"',
            'ps aux | grep "polkit-[m]ate-authentication-agent-1"',
            'ps aux | grep "[l]xpolkit"',
            'ps aux | grep "[l]xsession"',
            'ps aux | grep "[g]nome-shell"',
            'ps aux | grep "[f]ingerprint-polkit-agent"',
        ]
        is_running = [commands.getoutput(cmd) for cmd in polkit_options]

        return any(is_running)

    @classmethod
    def _is_pkexec_in_system(self):
        """
        Checks the existence of the pkexec binary in system.
        """
        pkexec_path = which('pkexec')
        if len(pkexec_path) == 0:
            return False
        return True
