# -*- coding: utf-8 -*-
# __init__.py
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
Services module.
"""
from PySide import QtCore
from leap.bitmask.util.privilege_policies import is_missing_policy_permissions

DEPLOYED = ["openvpn", "mx"]


def get_service_display_name(service, standalone=False):
    """
    Returns the name to display of the given service.
    If there is no configured name for that service, then returns the same
    parameter

    :param service: the 'machine' service name
    :type service: str
    :param standalone: True if the app is running in a standalone mode, used
                       to display messages according that.
    :type standalone: bool

    :rtype: str
    """
    # qt translator method helper
    _tr = QtCore.QObject().tr

    # Correspondence for services and their name to display
    EIP_LABEL = _tr("Encrypted Internet")
    MX_LABEL = _tr("Encrypted Mail")

    service_display = {
        "openvpn": EIP_LABEL,
        "mx": MX_LABEL
    }

    # If we need to add a warning about eip needing
    # administrative permissions to start. That can be either
    # because we are running in standalone mode, or because we could
    # not find the needed privilege escalation mechanisms being operative.
    if standalone or is_missing_policy_permissions():
        EIP_LABEL += " " + _tr("(will need admin password to start)")

    return service_display.get(service, service)


def get_supported(services):
    """
    Returns a list of the available services.

    :param services: a list containing the services to be filtered.
    :type services: list of str

    :returns: a list of the available services
    :rtype: list of str
    """
    return filter(lambda s: s in DEPLOYED, services)
