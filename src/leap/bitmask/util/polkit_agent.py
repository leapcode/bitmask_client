# -*- coding: utf-8 -*-
# polkit_agent.py
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
Daemonizes polkit authentication agent.
"""
import logging
import os
import subprocess

import daemon

logger = logging.getLogger(__name__)

AUTH_FILE = "polkit-%s-authentication-agent-1"
BASE_PATH_GNO = "/usr/lib/policykit-1-gnome/"
BASE_PATH_KDE = "/usr/lib/kde4/libexec/"
GNO_PATH = BASE_PATH_GNO + AUTH_FILE % ("gnome",)
KDE_PATH = BASE_PATH_KDE + AUTH_FILE % ("kde",)

POLKIT_PATHS = (
    '/usr/lib/lxpolkit/lxpolkit',
    '/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1',
    '/usr/lib/mate-polkit/polkit-mate-authentication-agent-1',
    '/usr/lib/kde4/libexec/polkit-kde-authentication-agent-1',
)


def _get_polkit_agent():
    """
    Return a valid polkit agent to use.

    :rtype: str or None
    """
    # TODO: in caso of having more than one polkit agent we may want to
    # stablish priorities. E.g.: lxpolkit over gnome-polkit for minimalistic
    # desktops.
    for polkit in POLKIT_PATHS:
        if os.path.isfile(polkit):
            return polkit

    return None


def _launch_agent():
    """
    Launch a polkit authentication agent on a subprocess.
    """
    polkit_agent = _get_polkit_agent()

    if polkit_agent is None:
        logger.erro("No usable polkit was found.")
        return

    logger.debug('Launching polkit auth agent')
    try:
        # XXX fix KDE launch. See: #3755
        subprocess.call(polkit_agent)
    except Exception as e:
        logger.error('Error launching polkit authentication agent %r' % (e, ))


def launch():
    """
    Launch a polkit authentication agent as a daemon.
    """
    with daemon.DaemonContext():
        _launch_agent()

if __name__ == "__main__":
    launch()
