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
import re
import getpass
import logging
import sys

from pixelated.config import arguments
from pixelated.config import logger as logger_config
from pixelated.bitmask_libraries.certs import LeapCertificate
from pixelated.bitmask_libraries.config import LeapConfig
from pixelated.bitmask_libraries.provider import LeapProvider
from pixelated.bitmask_libraries.session import LeapSessionFactory
from leap.auth import SRPAuth
from leap.common.events import server as events_server
import pixelated.extensions.shared_db


logger = logging.getLogger(__name__)


def register(
        server_name,
        username,
        password,
        leap_home,
        provider_cert,
        provider_cert_fingerprint):

    if not password:
        password = getpass.getpass('Please enter password for %s: ' % username)

    try:
        validate_username(username)
        validate_password(password)
    except ValueError, e:
        print(e.message)
        sys.exit(1)

    events_server.ensure_server()
    LeapCertificate.set_cert_and_fingerprint(
        provider_cert, provider_cert_fingerprint)
    config = LeapConfig(leap_home=leap_home)
    provider = LeapProvider(server_name, config)
    LeapCertificate(provider).setup_ca_bundle()
    srp_auth = SRPAuth(provider.api_uri, LeapCertificate(
        provider).provider_api_cert)

    if srp_auth.register(username, password):
        LeapSessionFactory(provider).create(username, password)
    else:
        logger.error("Register failed")


def validate_username(username):
    accepted_characters = '^[a-z0-9\-\_\.]*$'
    if (not re.match(accepted_characters, username)):
        raise ValueError('Only lowercase letters, digits, . - and _ allowed.')


def validate_password(password):
    if len(password) < 8:
        raise ValueError('The password must have at least 8 characters')


def initialize():
    logger_config.init(debug=False)
    args = arguments.parse_register_args()
    register(
        args.provider,
        args.username,
        args.password,
        args.leap_home,
        args.leap_provider_cert,
        args.leap_provider_cert_fingerprint)
