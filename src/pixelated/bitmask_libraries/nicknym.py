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
from leap.keymanager import KeyManager, openpgp, KeyNotFound
from .certs import LeapCertificate
from twisted.internet import defer
import logging

logger = logging.getLogger(__name__)


class NickNym(object):

    def __init__(self, provider, config, soledad, email_address, token, uuid):
        nicknym_url = _discover_nicknym_server(provider)
        self._email = email_address
        self.keymanager = KeyManager(self._email, nicknym_url,
                                     soledad,
                                     token=token, ca_cert_path=LeapCertificate(
                                         provider).provider_api_cert, api_uri=provider.api_uri,
                                     api_version=provider.api_version,
                                     uid=uuid, gpgbinary=config.gpg_binary)

    @defer.inlineCallbacks
    def generate_openpgp_key(self):
        key_present = yield self._key_exists(self._email)
        if not key_present:
            logger.info("Generating keys - this could take a while...")
            yield self._gen_key()
        yield self._send_key_to_leap()

    @defer.inlineCallbacks
    def _key_exists(self, email):
        try:
            yield self.fetch_key(email, private=True, fetch_remote=False)
            defer.returnValue(True)
        except KeyNotFound:
            defer.returnValue(False)

    def fetch_key(self, email, private=False, fetch_remote=True):
        return self.keymanager.get_key(email, openpgp.OpenPGPKey, private=private, fetch_remote=fetch_remote)

    def _gen_key(self):
        return self.keymanager.gen_key(openpgp.OpenPGPKey)

    def _send_key_to_leap(self):
        return self.keymanager.send_key(openpgp.OpenPGPKey)


def _discover_nicknym_server(provider):
    return 'https://nicknym.%s:6425/' % provider.domain
