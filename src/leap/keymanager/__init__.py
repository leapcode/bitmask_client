# -*- coding: utf-8 -*-
# __init__.py
# Copyright (C) 2013 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


"""
Key Manager is a Nicknym agent for LEAP client.
"""

import requests

try:
    import simplejson as json
except ImportError:
    import json  # noqa

from leap.common.check import leap_assert
from leap.keymanager.errors import (
    KeyNotFound,
    NoPasswordGiven,
)
from leap.keymanager.keys import (
    build_key_from_dict,
    KEYMANAGER_KEY_TAG,
    TAGS_PRIVATE_INDEX,
)
from leap.keymanager.openpgp import (
    OpenPGPKey,
    OpenPGPScheme,
)


#
# The Key Manager
#

class KeyManager(object):

    #
    # server's key storage constants
    #

    OPENPGP_KEY = 'openpgp'
    PUBKEY_KEY = "user[public_key]"

    def __init__(self, address, nickserver_uri, soledad, session_id=None,
                 ca_cert_path=None, api_uri=None, api_version=None, uid=None):
        """
        Initialize a Key Manager for user's C{address} with provider's
        nickserver reachable in C{url}.

        :param address: The address of the user of this Key Manager.
        :type address: str
        :param url: The URL of the nickserver.
        :type url: str
        :param soledad: A Soledad instance for local storage of keys.
        :type soledad: leap.soledad.Soledad
        :param session_id: The session ID for interacting with the webapp API.
        :type session_id: str
        :param ca_cert_path: The path to the CA certificate.
        :type ca_cert_path: str
        :param api_uri: The URI of the webapp API.
        :type api_uri: str
        :param api_version: The version of the webapp API.
        :type api_version: str
        :param uid: The users' UID.
        :type uid: str
        """
        self._address = address
        self._nickserver_uri = nickserver_uri
        self._soledad = soledad
        self._session_id = session_id
        self.ca_cert_path = ca_cert_path
        self.api_uri = api_uri
        self.api_version = api_version
        self.uid = uid
        # a dict to map key types to their handlers
        self._wrapper_map = {
            OpenPGPKey: OpenPGPScheme(soledad),
            # other types of key will be added to this mapper.
        }
        # the following are used to perform https requests
        self._fetcher = requests
        self._session = self._fetcher.session()

    #
    # utilities
    #

    def _key_class_from_type(self, ktype):
        """
        Return key class from string representation of key type.
        """
        return filter(
            lambda klass: str(klass) == ktype,
            self._wrapper_map).pop()

    def _get(self, uri, data=None):
        """
        Send a GET request to C{uri} containing C{data}.

        :param uri: The URI of the request.
        :type uri: str
        :param data: The body of the request.
        :type data: dict, str or file

        :return: The response to the request.
        :rtype: requests.Response
        """
        leap_assert(
            self._ca_cert_path is not None,
            'We need the CA certificate path!')
        res = self._fetcher.get(uri, data=data, verify=self._ca_cert_path)
        # assert that the response is valid
        res.raise_for_status()
        leap_assert(
            res.headers['content-type'].startswith('application/json'),
            'Content-type is not JSON.')
        return res

    def _put(self, uri, data=None):
        """
        Send a PUT request to C{uri} containing C{data}.

        The request will be sent using the configured CA certificate path to
        verify the server certificate and the configured session id for
        authentication.

        :param uri: The URI of the request.
        :type uri: str
        :param data: The body of the request.
        :type data: dict, str or file

        :return: The response to the request.
        :rtype: requests.Response
        """
        leap_assert(
            self._ca_cert_path is not None,
            'We need the CA certificate path!')
        leap_assert(
            self._session_id is not None,
            'We need a session_id to interact with webapp!')
        res = self._fetcher.put(
            uri, data=data, verify=self._ca_cert_path,
            cookies={'_session_id': self._session_id})
        # assert that the response is valid
        res.raise_for_status()
        return res

    def _fetch_keys_from_server(self, address):
        """
        Fetch keys bound to C{address} from nickserver and insert them in
        local database.

        :param address: The address bound to the keys.
        :type address: str

        @raise KeyNotFound: If the key was not found on nickserver.
        """
        # request keys from the nickserver
        server_keys = self._get(
            self._nickserver_uri, {'address': address}).json()
        # insert keys in local database
        if self.OPENPGP_KEY in server_keys:
            self._wrapper_map[OpenPGPKey].put_ascii_key(
                server_keys['openpgp'])

    #
    # key management
    #

    def send_key(self, ktype):
        """
        Send user's key of type C{ktype} to provider.

        Public key bound to user's is sent to provider, which will sign it and
        replace any prior keys for the same address in its database.

        If C{send_private} is True, then the private key is encrypted with
        C{password} and sent to server in the same request, together with a
        hash string of user's address and password. The encrypted private key
        will be saved in the server in a way it is publicly retrievable
        through the hash string.

        :param ktype: The type of the key.
        :type ktype: KeyType

        @raise KeyNotFound: If the key was not found in local database.
        """
        leap_assert(
            ktype is OpenPGPKey,
            'For now we only know how to send OpenPGP public keys.')
        # prepare the public key bound to address
        pubkey = self.get_key(
            self._address, ktype, private=False, fetch_remote=False)
        data = {
            self.PUBKEY_KEY: pubkey.key_data
        }
        uri = "%s/%s/users/%s.json" % (
            self._api_uri,
            self._api_version,
            self._uid)
        self._put(uri, data)

    def get_key(self, address, ktype, private=False, fetch_remote=True):
        """
        Return a key of type C{ktype} bound to C{address}.

        First, search for the key in local storage. If it is not available,
        then try to fetch from nickserver.

        :param address: The address bound to the key.
        :type address: str
        :param ktype: The type of the key.
        :type ktype: KeyType
        :param private: Look for a private key instead of a public one?
        :type private: bool

        :return: A key of type C{ktype} bound to C{address}.
        :rtype: EncryptionKey
        @raise KeyNotFound: If the key was not found both locally and in
            keyserver.
        """
        leap_assert(
            ktype in self._wrapper_map,
            'Unkown key type: %s.' % str(ktype))
        try:
            # return key if it exists in local database
            return self._wrapper_map[ktype].get_key(address, private=private)
        except KeyNotFound:
            # we will only try to fetch a key from nickserver if fetch_remote
            # is True and the key is not private.
            if fetch_remote is False or private is True:
                raise
            self._fetch_keys_from_server(address)
            return self._wrapper_map[ktype].get_key(address, private=False)

    def get_all_keys_in_local_db(self, private=False):
        """
        Return all keys stored in local database.

        :return: A list with all keys in local db.
        :rtype: list
        """
        return map(
            lambda doc: build_key_from_dict(
                self._key_class_from_type(doc.content['type']),
                doc.content['address'],
                doc.content),
            self._soledad.get_from_index(
                TAGS_PRIVATE_INDEX,
                KEYMANAGER_KEY_TAG,
                '1' if private else '0'))

    def refresh_keys(self):
        """
        Fetch keys from nickserver and update them locally.
        """
        addresses = set(map(
            lambda doc: doc.address,
            self.get_all_keys_in_local_db(private=False)))
        for address in addresses:
            # do not attempt to refresh our own key
            if address == self._address:
                continue
            self._fetch_keys_from_server(address)

    def gen_key(self, ktype):
        """
        Generate a key of type C{ktype} bound to the user's address.

        :param ktype: The type of the key.
        :type ktype: KeyType

        :return: The generated key.
        :rtype: EncryptionKey
        """
        return self._wrapper_map[ktype].gen_key(self._address)

    #
    # Setters/getters
    #

    def _get_session_id(self):
        return self._session_id

    def _set_session_id(self, session_id):
        self._session_id = session_id

    session_id = property(
        _get_session_id, _set_session_id, doc='The session id.')

    def _get_ca_cert_path(self):
        return self._ca_cert_path

    def _set_ca_cert_path(self, ca_cert_path):
        self._ca_cert_path = ca_cert_path

    ca_cert_path = property(
        _get_ca_cert_path, _set_ca_cert_path,
        doc='The path to the CA certificate.')

    def _get_api_uri(self):
        return self._api_uri

    def _set_api_uri(self, api_uri):
        self._api_uri = api_uri

    api_uri = property(
        _get_api_uri, _set_api_uri, doc='The webapp API URI.')

    def _get_api_version(self):
        return self._api_version

    def _set_api_version(self, api_version):
        self._api_version = api_version

    api_version = property(
        _get_api_version, _set_api_version, doc='The webapp API version.')

    def _get_uid(self):
        return self._uid

    def _set_uid(self, uid):
        self._uid = uid

    uid = property(
        _get_uid, _set_uid, doc='The uid of the user.')
