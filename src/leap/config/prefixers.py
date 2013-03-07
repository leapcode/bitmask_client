# -*- coding: utf-8 -*-
# prefixers.py
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
Platform dependant configuration path prefixers
"""
import os
import platform

from abc import ABCMeta, abstractmethod
from xdg import BaseDirectory

from leap.util.check import leap_assert


class Prefixer:
    """
    Abstract prefixer class
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def get_path_prefix(self, standalone=False):
        """
        Returns the platform dependant path prefixer

        @param standalone: if True it will return the prefix for a
        standalone application. Otherwise, it will return the system
        default for configuration storage.
        @param type: bool
        """
        return ""


def get_platform_prefixer():
    prefixer = globals()[platform.system() + "Prefixer"]
    leap_assert(prefixer, "Unimplemented platform prefixer: %s" %
                (platform.system(),))
    return prefixer()


class LinuxPrefixer(Prefixer):
    """
    Config prefixer for the Linux platform
    """

    def get_path_prefix(self, standalone=False):
        """
        Returns the platform dependant path prefixer.
        This method expects an env variable named LEAP_CLIENT_PATH if
        standalone is used.

        @param standalone: if True it will return the prefix for a
        standalone application. Otherwise, it will return the system
        default for configuration storage.
        @param type: bool
        """
        config_dir = BaseDirectory.xdg_config_home
        if not standalone:
            return config_dir
        return os.getenv("LEAP_CLIENT_PATH", config_dir)


if __name__ == "__main__":
    try:
        abs_prefixer = Prefixer()
    except Exception as e:
        assert isinstance(e, TypeError), "Something went wrong"
        print "Abstract Prefixer class is working as expected"

    linux_prefixer = LinuxPrefixer()
    print linux_prefixer.get_path_prefix(standalone=True)
    print linux_prefixer.get_path_prefix()
