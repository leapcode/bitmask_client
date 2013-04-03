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
import logging
import os
import platform

from abc import ABCMeta, abstractmethod

logger = logging.getLogger(__name__)


def is_missing_policy_permissions():
    """
    Returns True if we do not have implemented a policy checker for this
    platform, or if the policy checker exists but it cannot find the
    appropriate policy mechanisms in place.
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

        @rtype: bool
        """
        return True


class LinuxPolicyChecker(PolicyChecker):
    """
    PolicyChecker for Linux
    """
    LINUX_POLKIT_FILE = ("/usr/share/polkit-1/actions/"
                         "net.openvpn.gui.leap.policy")

    def is_missing_policy_permissions(self):
        """
        Returns True if we could not find the appropriate policykit file
        in place
        """
        return not os.path.isfile(self.LINUX_POLKIT_FILE)
