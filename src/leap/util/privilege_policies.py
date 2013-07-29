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


POLICY_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE policyconfig PUBLIC
 "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
<policyconfig>

  <vendor>LEAP Project</vendor>
  <vendor_url>https://leap.se/</vendor_url>

  <action id="net.openvpn.gui.leap.run-openvpn">
    <description>Runs the openvpn binary</description>
    <description xml:lang="es">Ejecuta el binario openvpn</description>
    <message>OpenVPN needs that you authenticate to start</message>
    <message xml:lang="es">
      OpenVPN necesita autorizacion para comenzar
    </message>
    <icon_name>package-x-generic</icon_name>
    <defaults>
      <allow_any>yes</allow_any>
      <allow_inactive>yes</allow_inactive>
      <allow_active>yes</allow_active>
    </defaults>
    <annotate key="org.freedesktop.policykit.exec.path">{path}</annotate>
    <annotate key="org.freedesktop.policykit.exec.allow_gui">true</annotate>
  </action>
</policyconfig>
"""


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


def get_policy_contents(openvpn_path):
    """
    Returns the contents that the policy file should have.

    :param openvpn_path: the openvpn path to use in the polkit file
    :type openvpn_path: str
    :rtype: str
    """
    return POLICY_TEMPLATE.format(path=openvpn_path)


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
                         "net.openvpn.gui.leap.policy")

    @classmethod
    def get_polkit_path(self):
        """
        Returns the polkit file path.

        :rtype: str
        """
        return self.LINUX_POLKIT_FILE

    def is_missing_policy_permissions(self):
        """
        Returns True if we could not find the appropriate policykit file
        in place

        :rtype: bool
        """
        return not os.path.isfile(self.LINUX_POLKIT_FILE)
