# Copyright 2011 Canonical Ltd.
#
# This file is part of u1db.
#
# u1db is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# u1db is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with u1db.  If not, see <http://www.gnu.org/licenses/>.

"""Command infrastructure for u1db"""

import argparse
import inspect


class CommandGroup(object):
    """A collection of commands."""

    def __init__(self, description=None):
        self.commands = {}
        self.description = description

    def register(self, cmd):
        """Register a new command to be incorporated with this group."""
        self.commands[cmd.name] = cmd

    def make_argparser(self):
        """Create an argparse.ArgumentParser"""
        parser = argparse.ArgumentParser(description=self.description)
        subs = parser.add_subparsers(title='commands')
        for name, cmd in sorted(self.commands.iteritems()):
            sub = subs.add_parser(name, help=cmd.__doc__)
            sub.set_defaults(subcommand=cmd)
            cmd._populate_subparser(sub)
        return parser

    def run_argv(self, argv, stdin, stdout, stderr):
        """Run a command, from a sys.argv[1:] style input."""
        parser = self.make_argparser()
        args = parser.parse_args(argv)
        cmd = args.subcommand(stdin, stdout, stderr)
        params, _, _, _ = inspect.getargspec(cmd.run)
        vals = []
        for param in params[1:]:
            vals.append(getattr(args, param))
        return cmd.run(*vals)


class Command(object):
    """Definition of a Command that can be run.

    :cvar name: The name of the command, so that you can run
        'u1db-client <name>'.
    """

    name = None

    def __init__(self, stdin, stdout, stderr):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

    @classmethod
    def _populate_subparser(cls, parser):
        """Child classes should override this to provide their arguments."""
        raise NotImplementedError(cls._populate_subparser)

    def run(self, *args):
        """This is where the magic happens.

        Subclasses should implement this, requesting their specific arguments.
        """
        raise NotImplementedError(self.run)
