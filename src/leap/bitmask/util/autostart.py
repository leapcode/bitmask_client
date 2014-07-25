# -*- coding: utf-8 -*-
# autostart.py
# Copyright (C) 2013, 2014 LEAP
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
Helpers to enable/disable bitmask's autostart.
"""
import logging
import os

from leap.bitmask.config import flags
from leap.bitmask.platform_init import IS_LINUX

logger = logging.getLogger(__name__)


DESKTOP_ENTRY = """\
[Desktop Entry]
Version=1.0
Encoding=UTF-8
Type=Application
Name=Bitmask
Comment=Secure Communication
Exec=bitmask --start-hidden
Terminal=false
Icon=bitmask
"""

DESKTOP_ENTRY_PATH = os.path.expanduser("~/.config/autostart/bitmask.desktop")


def set_autostart(enabled):
    """
    Set the autostart mode to enabled or disabled depending on the parameter.
    If `enabled` is `True`, save the autostart file to its place. Otherwise,
    remove that file.
    Right now we support only Linux autostart.

    :param enabled: whether the autostart should be enabled or not.
    :type enabled: bool
    """
    # we don't do autostart for bundle or systems different than Linux
    if flags.STANDALONE or not IS_LINUX:
        return

    if enabled:
        with open(DESKTOP_ENTRY_PATH, 'w') as f:
            f.write(DESKTOP_ENTRY)
    else:
        try:
            os.remove(DESKTOP_ENTRY_PATH)
        except OSError:  # if the file does not exist
            pass
        except Exception as e:
            logger.error("Problem disabling autostart, {0!r}".format(e))
