#!/usr/bin/env python
# init.py
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
Tool to initialize a TUF repo.

The keys can be generated with:
    openssl genrsa -des3 -out private.pem 4096
The public key can be exported with:
    openssl rsa -in private.pem -outform PEM -pubout -out public.pem
"""

import sys

from tuf.repository_tool import create_new_repository
from tuf.repository_tool import import_rsa_privatekey_from_file
from tuf.repository_tool import import_rsa_publickey_from_file


def usage():
    print ("Usage:  %s repo root_private_key root_pub_key targets_pub_key"
           " timestamp_pub_key") % (sys.argv[0],)


def main():
    if len(sys.argv) < 6:
        usage()
        return

    repo_path = sys.argv[1]
    root_priv_path = sys.argv[2]
    root_pub_path = sys.argv[3]
    targets_pub_path = sys.argv[4]
    timestamp_pub_path = sys.argv[5]
    repo = Repo(repo_path, root_priv_path)
    repo.build(root_pub_path, targets_pub_path, timestamp_pub_path)

    print "%s/metadata.staged/root.json is ready" % (repo_path,)


class Repo(object):
    """
    Repository builder class
    """

    def __init__(self, repo_path, key_path):
        """
        Constructor

        :param repo_path: path where the repo lives
        :type repo_path: str
        :param key_path: path where the private root key lives
        :type key_path: str
        """
        self._repo_path = repo_path
        self._key = import_rsa_privatekey_from_file(key_path)

    def build(self, root_pub_path, targets_pub_path, timestamp_pub_path):
        """
        Create a new repo

        :param root_pub_path: path where the public root key lives
        :type root_pub_path: str
        :param targets_pub_path: path where the public targets key lives
        :type targets_pub_path: str
        :param timestamp_pub_path: path where the public timestamp key lives
        :type timestamp_pub_path: str
        """
        repository = create_new_repository(self._repo_path)

        pub_root_key = import_rsa_publickey_from_file(root_pub_path)
        repository.root.add_verification_key(pub_root_key)
        repository.root.load_signing_key(self._key)

        pub_target_key = import_rsa_publickey_from_file(targets_pub_path)
        repository.targets.add_verification_key(pub_target_key)
        repository.snapshot.add_verification_key(pub_target_key)
        repository.targets.compressions = ["gz"]
        repository.snapshot.compressions = ["gz"]

        pub_timestamp_key = import_rsa_publickey_from_file(timestamp_pub_path)
        repository.timestamp.add_verification_key(pub_timestamp_key)

        repository.write_partial()


if __name__ == "__main__":
    main()
