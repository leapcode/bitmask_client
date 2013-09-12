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
import subprocess

import daemon

logger = logging.getLogger(__name__)

AUTH_FILE = "polkit-%s-authentication-agent-1"
BASE_PATH_GNO = "/usr/lib/policykit-1-gnome/"
BASE_PATH_KDE = "/usr/lib/kde4/libexec/"
GNO_PATH = BASE_PATH_GNO + AUTH_FILE % ("gnome",)
KDE_PATH = BASE_PATH_KDE + AUTH_FILE % ("kde",)


def _launch_agent():
    logger.debug('Launching polkit auth agent')
    try:
        subprocess.call(GNO_PATH)
    except Exception as exc:
        logger.error('Exception while running polkit authentication agent '
                     '%s' % (exc,))
        # XXX fix KDE launch. See: #3755
        #try:
            #subprocess.call(KDE_PATH)
        #except Exception as exc:


def launch():
    with daemon.DaemonContext():
        _launch_agent()

if __name__ == "__main__":
    launch()
