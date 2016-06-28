#!/usr/bin/env python
# -*- coding: utf-8 -*-
# bitmask_cli
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
Bitmask Command Line interface: zmq client.
"""
import json
import sys
import getpass
import argparse

from colorama import init as color_init
from colorama import Fore
from twisted.internet import reactor
from txzmq import ZmqEndpoint, ZmqEndpointType
from txzmq import ZmqFactory, ZmqREQConnection
from txzmq import ZmqRequestTimeoutError

from leap.bitmask.core import ENDPOINT


class BitmaskCLI(object):

    def __init__(self):
        parser = argparse.ArgumentParser(
            usage='''bitmask_cli <command> [<args>]

Controls the Bitmask application.

SERVICE COMMANDS:

   user       Handles Bitmask accounts
   mail       Bitmask Encrypted Mail
   eip        Encrypted Internet Proxy
   keys       Bitmask Keymanager

GENERAL COMMANDS:

   version    prints version number and exit
   launch     launch the Bitmask backend daemon
   shutdown   shutdown Bitmask backend daemon
   status     displays general status about the running Bitmask services
   debug      show some debug info about bitmask-core


''', epilog=("Use 'bitmask_cli <command> --help' to learn more "
             "about each command."))
        parser.add_argument('command', help='Subcommand to run')

        # parse_args defaults to [1:] for args, but you need to
        # exclude the rest of the args too, or validation will fail
        args = parser.parse_args(sys.argv[1:2])
        self.args = args
        self.subargs = None

        if not hasattr(self, args.command):
            print 'Unrecognized command'
            parser.print_help()
            exit(1)

        # use dispatch pattern to invoke method with same name
        getattr(self, args.command)()

    def user(self):
        parser = argparse.ArgumentParser(
            description=('Handles Bitmask accounts: creation, authentication '
                         'and modification'),
            prog='bitmask_cli user')
        parser.add_argument('username', nargs='?',
                            help='username ID, in the form <user@example.org>')
        parser.add_argument('--create', action='store_true',
                            help='register a new user, if possible')
        parser.add_argument('--authenticate', action='store_true',
                            help='logs in against the provider')
        parser.add_argument('--logout', action='store_true',
                            help='ends any active session with the provider')
        parser.add_argument('--active', action='store_true',
                            help='shows the active user, if any')
        # now that we're inside a subcommand, ignore the first
        # TWO argvs, ie the command (bitmask_cli) and the subcommand (user)
        args = parser.parse_args(sys.argv[2:])
        self.subargs = args

    def mail(self):
        parser = argparse.ArgumentParser(
            description='Bitmask Encrypted Mail service',
            prog='bitmask_cli mail')
        parser.add_argument('--start', action='store_true',
                            help='tries to start the mail service')
        parser.add_argument('--stop', action='store_true',
                            help='stops the mail service if running')
        parser.add_argument('--status', action='store_true',
                            help='displays status about the mail service')
        parser.add_argument('--enable', action='store_true')
        parser.add_argument('--disable', action='store_true')
        parser.add_argument('--get-token', action='store_true',
                            help='returns token for the mail service')
        parser.add_argument('--get-smtp-certificate', action='store_true',
                            help='downloads a new smtp certificate')
        parser.add_argument('--check-smtp-certificate', action='store_true',
                            help='downloads a new smtp certificate '
                            '(NOT IMPLEMENTED)')

        args = parser.parse_args(sys.argv[2:])
        self.subargs = args

    def eip(self):
        parser = argparse.ArgumentParser(
            description='Encrypted Internet Proxy service',
            prog='bitmask_cli eip')
        parser.add_argument('--start', action='store_true',
                            help='Start service')
        parser.add_argument('--stop', action='store_true', help='Stop service')
        parser.add_argument('--status', action='store_true',
                            help='Display status about service')
        parser.add_argument('--enable', action='store_true')
        parser.add_argument('--disable', action='store_true')
        args = parser.parse_args(sys.argv[2:])
        self.subargs = args

    def keys(self):
        parser = argparse.ArgumentParser(
            description='Bitmask Keymanager management service',
            prog='bitmask_cli keys')
        parser.add_argument('--list', action='store_true',
                            help='List all known keys')
        parser.add_argument('--export', action='store_true',
                            help='Export the given key')
        parser.add_argument('address', nargs='?',
                            help='email address of the key')
        args = parser.parse_args(sys.argv[2:])
        self.subargs = args

    # Single commands

    def launch(self):
        pass

    def shutdown(self):
        pass

    def status(self):
        pass

    def version(self):
        pass

    def debug(self):
        pass


def get_zmq_connection():
    zf = ZmqFactory()
    e = ZmqEndpoint(ZmqEndpointType.connect, ENDPOINT)
    return ZmqREQConnection(zf, e)


def error(msg, stop=False):
    print Fore.RED + "[!] %s" % msg + Fore.RESET
    if stop:
        reactor.stop()
    else:
        sys.exit(1)


def timeout_handler(failure, stop_reactor=True):
    # TODO ---- could try to launch the bitmask daemon here and retry

    if failure.trap(ZmqRequestTimeoutError) == ZmqRequestTimeoutError:
        print (Fore.RED + "[ERROR] Timeout contacting the bitmask daemon. "
               "Is it running?" + Fore.RESET)
        reactor.stop()


def do_print_result(stuff):
    obj = json.loads(stuff[0])
    if not obj['error']:
        print Fore.GREEN + '%s' % obj['result'] + Fore.RESET
    else:
        print Fore.RED + 'ERROR:' + '%s' % obj['error'] + Fore.RESET


def do_print_key(stuff):
    obj = json.loads(stuff[0])
    if obj['error']:
        do_print_result(stuff)
        return

    key = obj['result']
    print Fore.GREEN
    print "Uids:        " + ', '.join(key['uids'])
    print "Fingerprint: " + key['fingerprint']
    print "Length:      " + str(key['length'])
    print "Expiration:  " + key['expiry_date']
    print "Validation:  " + key['validation']
    print("Used:        " + "sig:" + str(key['sign_used']) +
          ", encr:" + str(key['encr_used']))
    print "Refresed:    " + key['refreshed_at']
    print Fore.RESET
    print ""
    print key['key_data']


def send_command(cli):

    args = cli.args
    subargs = cli.subargs
    cb = do_print_result

    cmd = args.command

    if cmd == 'launch':
        # XXX careful! Should see if the process in PID is running,
        # avoid launching again.
        import commands
        commands.getoutput('bitmaskd')
        reactor.stop()
        return

    elif cmd == 'version':
        do_print_result([json.dumps(
            {'result': 'bitmask_cli: 0.0.1',
             'error': None})])
        data = ('version',)

    elif cmd == 'status':
        data = ('status',)

    elif cmd == 'shutdown':
        data = ('shutdown',)

    elif cmd == 'debug':
        data = ('stats',)

    elif cmd == 'user':
        if 1 != (subargs.active + subargs.create +
                 subargs.authenticate + subargs.logout):
            error('Use bitmask_cli user --help to see available subcommands',
                  stop=True)
            return

        data = ['user']

        if subargs.active:
            data += ['active', '', '']

        else:
            if subargs.create:
                data.append('signup')
            elif subargs.authenticate:
                data.append('authenticate')
            elif subargs.logout:
                data.append('logout')

            username = subargs.username
            if username and '@' not in username:
                error("Username ID must be in the form <user@example.org>",
                      stop=True)
                return
            if not subargs.logout and not username:
                error("Missing username ID but needed for this command",
                      stop=True)
                return
            elif not username:
                username = ''
            data.append(username)

            if not subargs.logout:
                passwd = getpass.getpass()
                data.append(passwd)

    elif cmd == 'mail':
        data = ['mail']

        if subargs.status:
            data += ['status']

        elif subargs.enable:
            data += ['enable']

        elif subargs.disable:
            data += ['disable']

        elif subargs.get_token:
            data += ['get_token']

        elif subargs.get_smtp_certificate:
            data += ['get_smtp_certificate']

        else:
            error('Use bitmask_cli mail --help to see available subcommands',
                  stop=True)
            return

    elif cmd == 'eip':
        data = ['eip']

        if subargs.status:
            data += ['status']

        elif subargs.enable:
            data += ['enable']

        elif subargs.disable:
            data += ['disable']

        elif subargs.start:
            data += ['start']

        elif subargs.stop:
            data += ['stop']

        else:
            error('Use bitmask_cli eip --help to see available subcommands',
                  stop=True)
            return

    elif cmd == 'keys':
        data = ['keys']

        if subargs.list:
            data += ['list']

        elif subargs.export:
            data += ['export']
            cb = do_print_key

        else:
            error('Use bitmask_cli keys --help to see available subcommands',
                  stop=True)
            return

        if subargs.address:
            data.append(subargs.address)

    s = get_zmq_connection()

    d = s.sendMsg(*data, timeout=60)
    d.addCallback(cb)
    d.addCallback(lambda x: reactor.stop())
    d.addErrback(timeout_handler)


def main():
    color_init()
    cli = BitmaskCLI()
    reactor.callWhenRunning(reactor.callLater, 0, send_command, cli)
    reactor.run()

if __name__ == "__main__":
    main()
