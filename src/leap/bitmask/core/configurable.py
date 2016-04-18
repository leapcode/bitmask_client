# -*- coding: utf-8 -*-
# configurable.py
# Copyright (C) 2015, 2016 LEAP
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
Configurable Backend for Bitmask Service.
"""
import ConfigParser
import os

from twisted.application import service

from leap.common import files
from leap.common.config import get_path_prefix


DEFAULT_BASEDIR = os.path.join(get_path_prefix(), 'leap')


class MissingConfigEntry(Exception):
    """
    A required config entry was not found.
    """


class ConfigurableService(service.MultiService):

    config_file = u"bitmaskd.cfg"
    service_names = ('mail', 'eip', 'zmq', 'web')

    def __init__(self, basedir=DEFAULT_BASEDIR):
        service.MultiService.__init__(self)

        path = os.path.abspath(os.path.expanduser(basedir))
        if not os.path.isdir(path):
            files.mkdir_p(path)
        self.basedir = path

        # creates self.config
        self.read_config()

    def get_config(self, section, option, default=None, boolean=False):
        try:
            if boolean:
                return self.config.getboolean(section, option)

            item = self.config.get(section, option)
            return item

        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            if default is None:
                fn = self._get_config_path()
                raise MissingConfigEntry("%s is missing the [%s]%s entry"
                                         % fn, section, option)
            return default

    def set_config(self, section, option, value):
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, option, value)
        self.save_config()
        self.read_config()
        assert self.config.get(section, option) == value

    def read_config(self):
        self.config = ConfigParser.SafeConfigParser()
        bitmaskd_cfg = self._get_config_path()

        if not os.path.isfile(bitmaskd_cfg):
            self._create_default_config(bitmaskd_cfg)

        with open(bitmaskd_cfg, "rb") as f:
            self.config.readfp(f)

    def save_config(self):
        bitmaskd_cfg = self._get_config_path()
        with open(bitmaskd_cfg, 'wb') as f:
            self.config.write(f)

    def _create_default_config(self, path):
        with open(path, 'w') as outf:
            outf.write(DEFAULT_CONFIG)

    def _get_config_path(self):
        return os.path.join(self.basedir, self.config_file)


DEFAULT_CONFIG = """
[services]
mail = True
eip = True
zmq = True
web = False
"""
