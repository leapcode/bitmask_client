#!/usr/bin/env python
# release.py
# Copyright (C) 2014 LEAP
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
Tool to generate TUF related files after a release

The 'repo' folder should contain two folders:
  - 'metadata.staged' with all the jsons from the previows release
  - 'targets' where the release targets are
"""

import datetime
import os.path
import sys

from tuf.repository_tool import load_repository
from tuf.repository_tool import import_rsa_privatekey_from_file

"""
Days until the expiration of targets.json and snapshot.json. After this ammount
of days the TUF client won't accept this files.
"""
EXPIRATION_DAYS = 90


def usage():
    print "Usage:  %s repo key" % (sys.argv[0],)


def main():
    if len(sys.argv) < 3:
        usage()
        return

    repo_path = sys.argv[1]
    key_path = sys.argv[2]
    targets = Targets(repo_path, key_path)
    targets.build()

    print "%s/metadata.staged/(targets|snapshot).json[.gz] are ready" % \
          (repo_path,)


class Targets(object):
    """
    Targets builder class
    """

    def __init__(self, repo_path, key_path):
        """
        Constructor

        :param repo_path: path where the repo lives
        :type repo_path: str
        :param key_path: path where the private targets key lives
        :type key_path: str
        """
        self._repo_path = repo_path
        self._key = import_rsa_privatekey_from_file(key_path)

    def build(self):
        """
        Generate snapshot.json[.gz] and targets.json[.gz]
        """
        self._repo = load_repository(self._repo_path)
        self._load_targets()

        self._repo.targets.load_signing_key(self._key)
        self._repo.snapshot.load_signing_key(self._key)
        self._repo.targets.compressions = ["gz"]
        self._repo.snapshot.compressions = ["gz"]
        self._repo.snapshot.expiration = (
            datetime.datetime.now() +
            datetime.timedelta(days=EXPIRATION_DAYS))
        self._repo.targets.expiration = (
            datetime.datetime.now() +
            datetime.timedelta(days=EXPIRATION_DAYS))
        self._repo.write_partial()

    def _load_targets(self):
        """
        Load a list of targets
        """
        targets_path = os.path.join(self._repo_path, 'targets')
        target_list = self._repo.get_filepaths_in_directory(
            targets_path,
            recursive_walk=True,
            followlinks=True)

        self._remove_obsolete_targets(target_list)

        for target in target_list:
            octal_file_permissions = oct(os.stat(target).st_mode)[3:]
            custom_file_permissions = {
                'file_permissions': octal_file_permissions
            }
            self._repo.targets.add_target(target, custom_file_permissions)

    def _remove_obsolete_targets(self, target_list):
        """
        Remove obsolete targets from TUF targets

        :param target_list: list of targets on full path comming from TUF
                            get_filepaths_in_directory
        :type target_list: list(str)
        """
        targets_path = os.path.join(self._repo_path, 'targets')
        relative_path_list = map(lambda t: t.split("/targets")[1], target_list)
        removed_targets = (set(self._repo.targets.target_files.keys())
                           - set(relative_path_list))

        for target in removed_targets:
            target_rel_path = target
            if target[0] == '/':
                target_rel_path = target[1:]
            target_path = os.path.join(targets_path, target_rel_path)
            self._repo.targets.remove_target(target_path)


if __name__ == "__main__":
    main()
