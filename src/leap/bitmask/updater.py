# -*- coding: utf-8 -*-
# updater.py
# Copyright (C) 2014, 2015 LEAP
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
Updater check and download loop.
"""
import os
import shutil
import platform
import time
import threading
import ConfigParser
import tuf.client.updater

from leap.bitmask.logs.utils import get_logger
from leap.common.events import emit, catalog


logger = get_logger()


"""
Supported platforms.

Maps platform names from `platform.system() + "-" + platform.machine()` to the
platform names we use in the repos.
"""
bundles_per_platform = {
    "Linux-i386": "linux-i386",
    "Linux-i686": "linux-i386",
    "Linux-x86_64": "linux-x86_64",
}

CONFIG_PATH = "launcher.conf"
GENERAL_SECTION = "General"
DELAY_KEY = "updater_delay"


class Updater(threading.Thread):

    def __init__(self):
        """
        Initialize the list of mirrors, paths and other TUF dependencies from
        the config file
        """
        config = ConfigParser.ConfigParser()
        config.read(CONFIG_PATH)

        if config.has_section(GENERAL_SECTION) and \
                config.has_option(GENERAL_SECTION, DELAY_KEY):
            self.delay = config.getint(GENERAL_SECTION, DELAY_KEY)
        else:
            self.delay = 60

        self._load_mirrors(config)
        if not self.mirrors:
            logger.error("No updater mirrors found (missing or not well "
                         "formed launcher.conf)")

        self.bundle_path = os.getcwd()
        self.source_path = self.bundle_path
        self.dest_path = os.path.join(self.bundle_path, 'tmp')
        self.update_path = os.path.join(self.bundle_path, 'updates')

        tuf.conf.ssl_certificates = "./lib/leap/common/cacert.pem"

        threading.Thread.__init__(self)
        self.daemon = True

    def run(self):
        """
        Check for updates
        """
        if not self.mirrors:
            return

        while True:
            try:
                tuf.conf.repository_directory = os.path.join(self.bundle_path,
                                                             'repo')

                updater = tuf.client.updater.Updater('leap-updater',
                                                     self.mirrors)
                updater.refresh()

                targets = updater.all_targets()
                updated_targets = updater.updated_targets(targets,
                                                          self.source_path)
                if updated_targets:
                    logger.info("There is updates needed. Start downloading "
                                "updates.")
                for target in updated_targets:
                    updater.download_target(target, self.dest_path)
                    self._set_permissions(target)
                if os.path.isdir(self.dest_path):
                    if os.path.isdir(self.update_path):
                        shutil.rmtree(self.update_path)
                    shutil.move(self.dest_path, self.update_path)
                    filepath = sorted([f['filepath'] for f in updated_targets])
                    emit(catalog.UPDATER_NEW_UPDATES,
                         ", ".join(filepath))
                    logger.info("Updates ready: %s" % (filepath,))
                    return
            except NotImplemented as e:
                logger.error("NotImplemented: %s" % (e,))
                return
            except Exception as e:
                logger.error("An unexpected error has occurred while "
                             "updating: %s" % (e,))
            finally:
                time.sleep(self.delay)

    def _load_mirrors(self, config):
        """
        Retrieve the mirrors from config and place them in self.mirrors

        :param config: parsed configuration file
        :type config: ConfigParser
        """
        self.mirrors = {}
        for section in config.sections():
            if section[:6] != 'Mirror':
                continue
            url_prefix = config.get(section, 'url_prefix')
            metadata_path = self._repo_path() + '/metadata'
            targets_path = self._repo_path() + '/targets'
            self.mirrors[section[7:]] = {'url_prefix': url_prefix,
                                         'metadata_path': metadata_path,
                                         'targets_path': targets_path,
                                         'confined_target_dirs': ['']}

    def _set_permissions(self, target):
        """
        Walk over all the targets and set the rigt permissions on each file.
        The permisions are stored in the custom field 'file_permissions' of the
        TUF's targets.json

        :param target: the already parsed target json
        :type target: tuf.formats.TARGETFILES_SCHEMA
        """
        file_permissions_str = target["fileinfo"]["custom"]["file_permissions"]
        file_permissions = int(file_permissions_str, 8)
        filepath = target['filepath']
        if filepath[0] == '/':
            filepath = filepath[1:]
        file_path = os.path.join(self.dest_path, filepath)
        os.chmod(file_path, file_permissions)

    def _repo_path(self):
        """
        Find the remote repo path deneding on the platform.

        :return: the path to add to the remote repo url for the specific
                 platform.
        :rtype: str

        :raises NotImplemented: When the system where bitmask is running is not
                                supported by the updater.
        """
        system = platform.system() + "-" + platform.machine()
        if system not in bundles_per_platform:
            raise NotImplementedError("Platform %s not supported" % (system,))
        return bundles_per_platform[system]
