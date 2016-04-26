#
# Copyright (c) 2015 ThoughtWorks, Inc.
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
import getpass
import json
import sys
import ConfigParser


def read(organization_mode, credentials_file):
    if organization_mode:
        return read_from_dispatcher()
    else:
        if credentials_file:
            return read_from_file(credentials_file)
        return prompt_for_credentials()


def prompt_for_credentials():
    provider = raw_input('Which provider do you want to connect to:\n')
    username = raw_input('What\'s your username registered on the provider:\n')
    password = getpass.getpass('Type your password:\n')
    return provider, username, password


def read_from_file(credentials_file):
    config_parser = ConfigParser.ConfigParser()
    credentials_file_path = os.path.abspath(
        os.path.expanduser(credentials_file))
    config_parser.read(credentials_file_path)
    provider, user, password = \
        config_parser.get('pixelated', 'leap_server_name'), \
        config_parser.get('pixelated', 'leap_username'), \
        config_parser.get('pixelated', 'leap_password')
    return provider, user, password


def read_from_dispatcher():
    config = json.loads(sys.stdin.read())
    return config['leap_provider_hostname'], config['user'], config['password']
