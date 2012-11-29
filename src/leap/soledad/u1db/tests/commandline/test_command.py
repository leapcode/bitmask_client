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

import cStringIO
import argparse

from u1db import (
    tests,
    )
from u1db.commandline import (
    command,
    )


class MyTestCommand(command.Command):
    """Help String"""

    name = 'mycmd'

    @classmethod
    def _populate_subparser(cls, parser):
        parser.add_argument('foo')
        parser.add_argument('--bar', dest='nbar', type=int)

    def run(self, foo, nbar):
        self.stdout.write('foo: %s nbar: %d' % (foo, nbar))
        return 0


def make_stdin_out_err():
    return cStringIO.StringIO(), cStringIO.StringIO(), cStringIO.StringIO()


class TestCommandGroup(tests.TestCase):

    def trap_system_exit(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SystemExit, e:
            self.fail('Got SystemExit trying to run: %s' % (func,))

    def parse_args(self, parser, args):
        return self.trap_system_exit(parser.parse_args, args)

    def test_register(self):
        group = command.CommandGroup()
        self.assertEqual({}, group.commands)
        group.register(MyTestCommand)
        self.assertEqual({'mycmd': MyTestCommand},
                         group.commands)

    def test_make_argparser(self):
        group = command.CommandGroup(description='test-foo')
        parser = group.make_argparser()
        self.assertIsInstance(parser, argparse.ArgumentParser)

    def test_make_argparser_with_command(self):
        group = command.CommandGroup(description='test-foo')
        group.register(MyTestCommand)
        parser = group.make_argparser()
        args = self.parse_args(parser, ['mycmd', 'foozizle', '--bar=10'])
        self.assertEqual('foozizle', args.foo)
        self.assertEqual(10, args.nbar)
        self.assertEqual(MyTestCommand, args.subcommand)

    def test_run_argv(self):
        group = command.CommandGroup()
        group.register(MyTestCommand)
        stdin, stdout, stderr = make_stdin_out_err()
        ret = self.trap_system_exit(group.run_argv,
                                    ['mycmd', 'foozizle', '--bar=10'],
                                    stdin, stdout, stderr)
        self.assertEqual(0, ret)


class TestCommand(tests.TestCase):

    def make_command(self):
        stdin, stdout, stderr = make_stdin_out_err()
        return command.Command(stdin, stdout, stderr)

    def test__init__(self):
        cmd = self.make_command()
        self.assertIsNot(None, cmd.stdin)
        self.assertIsNot(None, cmd.stdout)
        self.assertIsNot(None, cmd.stderr)

    def test_run_args(self):
        stdin, stdout, stderr = make_stdin_out_err()
        cmd = MyTestCommand(stdin, stdout, stderr)
        res = cmd.run(foo='foozizle', nbar=10)
        self.assertEqual('foo: foozizle nbar: 10', stdout.getvalue())
