# -*- coding: utf-8 -*-
# user
# Copyright (C) 2016 LEAP
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
Bitmask Command Line interface: user
"""
import argparse
import getpass
import sys

from leap.bitmask.cli.command import Command


class User(Command):
    service = 'user'
    usage = '''%s user <subcommand>

Bitmask account service

SUBCOMMANDS:

   create     Register a new user, if possible
   auth       Logs in gainst the provider
   logout     Ends any active session with the provider
   active     Shows the active user, if any

''' % sys.argv[0]

    commands = ['active']

    def create(self, raw_args):
        username = self.username(raw_args)
        passwd = getpass.getpass()
        self.data += ['signup', username, passwd]
        return self._send()

    def auth(self, raw_args):
        username = self.username(raw_args)
        passwd = getpass.getpass()
        self.data += ['authenticate', username, passwd]
        return self._send()

    def logout(self, raw_args):
        username = self.username(raw_args)
        self.data += ['logout', username]
        return self._send()

    def username(self, raw_args):
        parser = argparse.ArgumentParser(
            description='Bitmask user',
            prog='%s %s %s' % tuple(sys.argv[:3]))
        parser.add_argument('username', nargs=1,
                            help='username ID, in the form <user@example.org>')
        subargs = parser.parse_args(raw_args)

        username = subargs.username[0]
        if not username:
            self._error("Missing username ID but needed for this command")
        if '@' not in username:
            self._error("Username ID must be in the form <user@example.org>")

        return username
