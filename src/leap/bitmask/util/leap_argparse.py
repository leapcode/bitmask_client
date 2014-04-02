# -*- coding: utf-8 -*-
# leap_argparse.py
# Copyright (C) 2013 LEAP
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
Parses the command line arguments passed to the application.
"""
import argparse

from leap.bitmask import IS_RELEASE_VERSION


def build_parser():
    """
    All the options for the leap arg parser
    Some of these could be switched on only if debug flag is present!
    """
    parser = argparse.ArgumentParser(
        description="Launches the Bitmask client.",
        epilog="Copyright 2012-2014 The LEAP Encryption Access Project")

    parser.add_argument('-d', '--debug', action="store_true",
                        help=("Launches Bitmask in debug mode, writing debug "
                              "info to stdout."))
    parser.add_argument('-V', '--version', action="store_true",
                        help='Displays Bitmask version and exits.')

    # files
    parser.add_argument('-l', '--logfile', metavar="LOG FILE", nargs='?',
                        action="store", dest="log_file",
                        help='Optional log file.')
    parser.add_argument('-m', '--mail-logfile',
                        metavar="MAIL LOG FILE", nargs='?',
                        action="store", dest="mail_log_file",
                        help='Optional log file for email.')

    # flags
    parser.add_argument('-s', '--standalone', action="store_true",
                        help='Makes Bitmask use standalone '
                        'directories for configuration and binary '
                        'searching.')
    parser.add_argument('-N', '--no-app-version-check', default=True,
                        action="store_false", dest="app_version_check",
                        help='Skip the app version compatibility check with '
                        'the provider.')
    parser.add_argument('-M', '--no-api-version-check', default=True,
                        action="store_false", dest="api_version_check",
                        help='Skip the api version compatibility check with '
                        'the provider.')

    # openvpn options
    parser.add_argument('--openvpn-verbosity', nargs='?',
                        type=int,
                        action="store", dest="openvpn_verb",
                        help='Verbosity level for openvpn logs [1-6]')

    # mail stuff
    parser.add_argument('-o', '--offline', action="store_true",
                        help='Starts Bitmask in offline mode: will not '
                             'try to sync with remote replicas for email.')

    parser.add_argument('--acct', metavar="user@provider",
                        nargs='?',
                        action="store", dest="acct",
                        help='Manipulate mailboxes for this account')
    parser.add_argument('-r', '--repair-mailboxes', default=False,
                        action="store_true", dest="repair",
                        help='Repair mailboxes for a given account. '
                             'Use when upgrading versions after a schema '
                             'change. Use with --acct')
    parser.add_argument('--import-maildir', metavar="/path/to/Maildir",
                        nargs='?',
                        action="store", dest="import_maildir",
                        help='Import the given maildir. Use with the '
                             '--to-mbox flag to import to folders other '
                             'than INBOX. Use with --acct')

    if not IS_RELEASE_VERSION:
        help_text = ("Bypasses the certificate check during provider "
                     "bootstraping, for debugging development servers. "
                     "Use at your own risk!")
        parser.add_argument('--danger', action="store_true", help=help_text)

    # optional cert file used to check domains with self signed certs.
    parser.add_argument('--ca-cert-file', metavar="/path/to/cacert.pem",
                        nargs='?', action="store", dest="ca_cert_file",
                        help='Uses the given cert file to verify '
                             'against domains.')

    # Not in use, we might want to reintroduce them.
    #parser.add_argument('-i', '--no-provider-checks',
                        #action="store_true", default=False,
                        #help="skips download of provider config files. gets "
                        #"config from local files only. Will fail if cannot "
                        #"find any")
    #parser.add_argument('-k', '--no-ca-verify',
                        #action="store_true", default=False,
                        #help="(insecure). Skips verification of the server "
                        #"certificate used in TLS handshake.")
    #parser.add_argument('-c', '--config', metavar="CONFIG FILE", nargs='?',
                        #action="store", dest="config_file",
                        #type=argparse.FileType('r'),
                        #help='optional config file')
    return parser


def init_leapc_args():
    parser = build_parser()
    opts, unknown = parser.parse_known_args()
    return parser, opts
