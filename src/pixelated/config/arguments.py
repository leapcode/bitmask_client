#
# Copyright (c) 2014 ThoughtWorks, Inc.
#
# Pixelated is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pixelated is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Pixelated. If not, see <http://www.gnu.org/licenses/>.

import os
import argparse


def parse_user_agent_args():
    parser = argparse.ArgumentParser(description='Pixelated user agent.')

    parser_add_default_arguments(parser)

    parser.add_argument('--host', default='127.0.0.1',
                        help='the host to run the user agent on')
    parser.add_argument('--organization-mode', help='Runs the user agent in organization mode, the credentials will be received from the stdin',
                        default=False, action='store_true', dest='organization_mode')
    parser.add_argument('--port', type=int, default=3333,
                        help='the port to run the user agent on')
    parser.add_argument('-sk', '--sslkey', metavar='<server.key>', default=None,
                        help='use specified file as web server\'s SSL key (when using the user-agent together with the pixelated-dispatcher)')
    parser.add_argument('-sc', '--sslcert', metavar='<server.crt>', default=None,
                        help='use specified file as web server\'s SSL certificate (when using the user-agent together with the pixelated-dispatcher)')
    parser.add_argument('--multi-user', help='Run user agent in multi user mode',
                        action='store_false', default=True, dest='single_user')
    parser.add_argument('-p', '--provider', help='specify a provider for mutli-user mode',
                        metavar='<provider host>', default=None, dest='provider')
    parser.add_argument('--banner', help='banner file to show on login screen')

    args = parser.parse_args()

    return args


def parse_maintenance_args():
    parser = argparse.ArgumentParser(description='Pixelated maintenance')
    parser_add_default_arguments(parser)
    subparsers = parser.add_subparsers(help='commands', dest='command')
    subparsers.add_parser('reset', help='reset account command')
    mails_parser = subparsers.add_parser(
        'load-mails', help='load mails into account')
    mails_parser.add_argument('file', nargs='+', help='file(s) with mail data')

    markov_mails_parser = subparsers.add_parser(
        'markov-generate', help='generate mails using markov chains')
    markov_mails_parser.add_argument(
        '--seed', default=None, help='Specify a seed to always generate the same output')
    markov_mails_parser.add_argument('-l', '--limit', metavar='count',
                                     default='5', help='limit number of generated mails', dest='limit')
    markov_mails_parser.add_argument(
        'file', nargs='+', help='file(s) with mail data')

    subparsers.add_parser('dump-soledad', help='dump the soledad database')
    subparsers.add_parser('sync', help='sync the soledad database')
    subparsers.add_parser('repair', help='repair database if possible')
    subparsers.add_parser(
        'integrity-check', help='run integrity check on database')

    return parser.parse_args()


def parse_register_args():
    parser = argparse.ArgumentParser(description='Pixelated register')
    parser.add_argument('provider', metavar='provider', action='store')
    parser.add_argument('username', metavar='username', action='store')
    parser.add_argument('-p', '--password', metavar='password', action='store',
                        default=None, help='used just to register account automatically by scripts')
    parser.add_argument('-lc', '--leap-provider-cert', metavar='<leap-provider.crt>', default=None,
                        help='use specified file for LEAP provider cert authority certificate (url https://<LEAP-provider-domain>/ca.crt)')
    parser.add_argument('-lf', '--leap-provider-cert-fingerprint', metavar='<leap provider certificate fingerprint>', default=None,
                        help='use specified fingerprint to validate connection with LEAP provider', dest='leap_provider_cert_fingerprint')
    parser.add_argument('--leap-home', help='The folder where the user agent stores its data. Defaults to ~/.leap',
                        dest='leap_home', default=os.path.join(os.path.expanduser("~"), '.leap'))
    return parser.parse_args()


def parser_add_default_arguments(parser):
    parser.add_argument('--debug', action='store_true', help='DEBUG mode.')
    parser.add_argument('-c', '--config', dest='credentials_file', metavar='<credentials_file>',
                        default=None, help='use specified file for credentials (for test purposes only)')
    parser.add_argument('--leap-home', help='The folder where the user agent stores its data. Defaults to ~/.leap',
                        dest='leap_home', default=os.path.join(os.path.expanduser("~"), '.leap'))
    parser.add_argument('-lc', '--leap-provider-cert', metavar='<leap-provider.crt>', default=None,
                        help='use specified file for LEAP provider cert authority certificate (url https://<LEAP-provider-domain>/ca.crt)')
    parser.add_argument('-lf', '--leap-provider-cert-fingerprint', metavar='<leap provider certificate fingerprint>', default=None,
                        help='use specified fingerprint to validate connection with LEAP provider', dest='leap_provider_cert_fingerprint')
