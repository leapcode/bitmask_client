# -*- coding: utf-8 -*-
# sender
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
Bitmask Command Line interface: zmq sender.
"""
import argparse
import json
import sys

from colorama import init as color_init
from colorama import Fore
from twisted.internet import defer
from txzmq import ZmqEndpoint, ZmqEndpointType
from txzmq import ZmqFactory, ZmqREQConnection
from txzmq import ZmqRequestTimeoutError

from leap.bitmask.core import ENDPOINT


def _print_result(result):
    print Fore.GREEN + '%s' % result + Fore.RESET


class Command(object):
    service = ''
    usage = '''%s %s <subcommand>''' % tuple(sys.argv[:2])
    epilog = ("Use '%s %s <subcommand> --help' to learn more "
              "about each command." % tuple(sys.argv[:2]))
    commands = []

    def __init__(self):
        color_init()
        zf = ZmqFactory()
        e = ZmqEndpoint(ZmqEndpointType.connect, ENDPOINT)
        self._conn = ZmqREQConnection(zf, e)

        self.data = []
        if self.service:
            self.data = [self.service]

    def execute(self, raw_args):
        self.parser = argparse.ArgumentParser(usage=self.usage,
                                              epilog=self.epilog)
        self.parser.add_argument('command', help='Subcommand to run')
        try:
            args = self.parser.parse_args(raw_args[0:1])
        except SystemExit:
            return defer.succeed(None)

        if args.command in self.commands:
            self.data += [args.command]
            return self._send()

        elif (args.command == 'execute' or
                args.command.startswith('_') or
                not hasattr(self, args.command)):
            print 'Unrecognized command'
            return self.help([])

        try:
            # use dispatch pattern to invoke method with same name
            return getattr(self, args.command)(raw_args[1:])
        except SystemExit:
            return defer.succeed(None)

    def help(self, raw_args):
        self.parser.print_help()
        return defer.succeed(None)

    def _send(self, cb=_print_result):
        d = self._conn.sendMsg(*self.data, timeout=60)
        d.addCallback(self._check_err, cb)
        d.addErrback(self._timeout_handler)
        return d

    def _error(self, msg):
        print Fore.RED + "[!] %s" % msg + Fore.RESET
        sys.exit(1)

    def _check_err(self, stuff, cb):
        obj = json.loads(stuff[0])
        if not obj['error']:
            return cb(obj['result'])
        else:
            print Fore.RED + 'ERROR:' + '%s' % obj['error'] + Fore.RESET

    def _timeout_handler(self, failure):
        # TODO ---- could try to launch the bitmask daemon here and retry
        if failure.trap(ZmqRequestTimeoutError) == ZmqRequestTimeoutError:
            print (Fore.RED + "[ERROR] Timeout contacting the bitmask daemon. "
                   "Is it running?" + Fore.RESET)
