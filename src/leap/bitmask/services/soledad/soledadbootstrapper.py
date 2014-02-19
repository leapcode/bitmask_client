# -*- coding: utf-8 -*-
# soledadbootstrapper.py
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
Soledad bootstrapping
"""
import logging
import os
import socket
import sys

from ssl import SSLError
from sqlite3 import ProgrammingError as sqlite_ProgrammingError

from PySide import QtCore
from u1db import errors as u1db_errors
from twisted.internet import threads
from zope.proxy import sameProxiedObjects
from pysqlcipher.dbapi2 import ProgrammingError as sqlcipher_ProgrammingError

from leap.bitmask.config import flags
from leap.bitmask.config.providerconfig import ProviderConfig
from leap.bitmask.crypto.srpauth import SRPAuth
from leap.bitmask.services import download_service_config
from leap.bitmask.services.abstractbootstrapper import AbstractBootstrapper
from leap.bitmask.services.soledad.soledadconfig import SoledadConfig
from leap.bitmask.util import first, is_file, is_empty_file, make_address
from leap.bitmask.util import get_path_prefix
from leap.bitmask.platform_init import IS_WIN
from leap.common.check import leap_assert, leap_assert_type, leap_check
from leap.common.files import which
from leap.keymanager import KeyManager, openpgp
from leap.keymanager.errors import KeyNotFound
from leap.soledad.client import Soledad, BootstrapSequenceError

logger = logging.getLogger(__name__)

"""
These mocks are replicated from imap tests and the repair utility.
They are needed for the moment to knock out the remote capabilities of soledad
during the use of the offline mode.

They should not be needed after we allow a null remote initialization in the
soledad client, and a switch to remote sync-able mode during runtime.
"""


class Mock(object):
    """
    A generic simple mock class
    """
    def __init__(self, return_value=None):
        self._return = return_value

    def __call__(self, *args, **kwargs):
        return self._return


class MockSharedDB(object):
    """
    Mocked  SharedDB object to replace in soledad before
    instantiating it in offline mode.
    """
    get_doc = Mock()
    put_doc = Mock()
    lock = Mock(return_value=('atoken', 300))
    unlock = Mock(return_value=True)

    def __call__(self):
        return self

# TODO these exceptions could be moved to soledad itself
# after settling this down.


class SoledadSyncError(Exception):
    message = "Error while syncing Soledad"


class SoledadInitError(Exception):
    message = "Error while initializing Soledad"


def get_db_paths(uuid):
    """
    Return the secrets and local db paths needed for soledad
    initialization

    :param uuid: uuid for user
    :type uuid: str

    :return: a tuple with secrets, local_db paths
    :rtype: tuple
    """
    prefix = os.path.join(get_path_prefix(), "leap", "soledad")
    secrets = "%s/%s.secret" % (prefix, uuid)
    local_db = "%s/%s.db" % (prefix, uuid)

    # We remove an empty file if found to avoid complains
    # about the db not being properly initialized
    if is_file(local_db) and is_empty_file(local_db):
        try:
            os.remove(local_db)
        except OSError:
            logger.warning(
                "Could not remove empty file %s"
                % local_db)
    return secrets, local_db


class SoledadBootstrapper(AbstractBootstrapper):
    """
    Soledad init procedure.
    """
    SOLEDAD_KEY = "soledad"
    KEYMANAGER_KEY = "keymanager"

    PUBKEY_KEY = "user[public_key]"

    MAX_INIT_RETRIES = 10
    MAX_SYNC_RETRIES = 10

    # All dicts returned are of the form
    # {"passed": bool, "error": str}
    download_config = QtCore.Signal(dict)
    gen_key = QtCore.Signal(dict)
    local_only_ready = QtCore.Signal(dict)
    soledad_timeout = QtCore.Signal()
    soledad_failed = QtCore.Signal()

    def __init__(self):
        AbstractBootstrapper.__init__(self)

        self._provider_config = None
        self._soledad_config = None
        self._keymanager = None
        self._download_if_needed = False

        self._user = ""
        self._password = ""
        self._address = ""
        self._uuid = ""

        self._srpauth = None
        self._soledad = None

        self._soledad_retries = 0

    @property
    def keymanager(self):
        return self._keymanager

    @property
    def soledad(self):
        return self._soledad

    @property
    def srpauth(self):
        if flags.OFFLINE is True:
            return None
        leap_assert(self._provider_config is not None,
                    "We need a provider config")
        return SRPAuth(self._provider_config)

    # retries

    def cancel_bootstrap(self):
        self._soledad_retries = self.MAX_INIT_RETRIES

    def should_retry_initialization(self):
        """
        Return True if we should retry the initialization.
        """
        logger.debug("current retries: %s, max retries: %s" % (
            self._soledad_retries,
            self.MAX_INIT_RETRIES))
        return self._soledad_retries < self.MAX_INIT_RETRIES

    def increment_retries_count(self):
        """
        Increment the count of initialization retries.
        """
        self._soledad_retries += 1

    # initialization

    def load_offline_soledad(self, username, password, uuid):
        """
        Instantiate Soledad for offline use.

        :param username: full user id (user@provider)
        :type username: basestring
        :param password: the soledad passphrase
        :type password: unicode
        :param uuid: the user uuid
        :type uuid: basestring
        """
        print "UUID ", uuid
        self._address = username
        self._uuid = uuid
        return self.load_and_sync_soledad(uuid, offline=True)

    def _get_soledad_local_params(self, uuid, offline=False):
        """
        Return the locals parameters needed for the soledad initialization.

        :param uuid: the uuid of the user, used in offline mode.
        :type uuid: unicode, or None.
        :return: secrets_path, local_db_path, token
        :rtype: tuple
        """
        # in the future, when we want to be able to switch to
        # online mode, this should be a proxy object too.
        # Same for server_url below.

        if offline is False:
            token = self.srpauth.get_token()
        else:
            token = ""

        secrets_path, local_db_path = get_db_paths(uuid)

        logger.debug('secrets_path:%s' % (secrets_path,))
        logger.debug('local_db:%s' % (local_db_path,))
        return (secrets_path, local_db_path, token)

    def _get_soledad_server_params(self, uuid, offline):
        """
        Return the remote parameters needed for the soledad initialization.

        :param uuid: the uuid of the user, used in offline mode.
        :type uuid: unicode, or None.
        :return: server_url, cert_file
        :rtype: tuple
        """
        if uuid is None:
            uuid = self.srpauth.get_uuid()

        if offline is True:
            server_url = "http://localhost:9999/"
            cert_file = ""
        else:
            server_url = self._pick_server(uuid)
            cert_file = self._provider_config.get_ca_cert_path()

        return server_url, cert_file

    def load_and_sync_soledad(self, uuid=None, offline=False):
        """
        Once everthing is in the right place, we instantiate and sync
        Soledad

        :param uuid: the uuid of the user, used in offline mode.
        :type uuid: unicode, or None.
        :param offline: whether to instantiate soledad for offline use.
        :type offline: bool
        """
        local_param = self._get_soledad_local_params(uuid, offline)
        remote_param = self._get_soledad_server_params(uuid, offline)

        secrets_path, local_db_path, token = local_param
        server_url, cert_file = remote_param

        try:
            self._try_soledad_init(
                uuid, secrets_path, local_db_path,
                server_url, cert_file, token)
        except Exception:
            # re-raise the exceptions from try_init,
            # we're currently handling the retries from the
            # soledad-launcher in the gui.
            raise

        leap_assert(not sameProxiedObjects(self._soledad, None),
                    "Null soledad, error while initializing")

        if flags.OFFLINE is True:
            self._init_keymanager(self._address, token)
            self.local_only_ready.emit({self.PASSED_KEY: True})
        else:
            try:
                address = make_address(
                    self._user, self._provider_config.get_domain())
                self._init_keymanager(address, token)
                self._keymanager.get_key(
                    address, openpgp.OpenPGPKey,
                    private=True, fetch_remote=False)
                threads.deferToThread(self._do_soledad_sync)
            except KeyNotFound:
                logger.debug("Key not found. Generating key for %s" %
                             (address,))
                self._do_soledad_sync()

    def _pick_server(self, uuid):
        """
        Choose a soledad server to sync against.

        :param uuid: the uuid for the user.
        :type uuid: unicode
        :returns: the server url
        :rtype: unicode
        """
        # TODO: Select server based on timezone (issue #3308)
        server_dict = self._soledad_config.get_hosts()

        if not server_dict.keys():
            # XXX raise more specific exception, and catch it properly!
            raise Exception("No soledad server found")

        selected_server = server_dict[first(server_dict.keys())]
        server_url = "https://%s:%s/user-%s" % (
            selected_server["hostname"],
            selected_server["port"],
            uuid)
        logger.debug("Using soledad server url: %s" % (server_url,))
        return server_url

    def _do_soledad_sync(self):
        """
        Do several retries to get an initial soledad sync.
        """
        # and now, let's sync
        sync_tries = self.MAX_SYNC_RETRIES
        while sync_tries > 0:
            try:
                self._try_soledad_sync()
                logger.debug("Soledad has been synced.")
                # so long, and thanks for all the fish
                return
            except SoledadSyncError:
                # maybe it's my connection, but I'm getting
                # ssl handshake timeouts and read errors quite often.
                # A particularly big sync is a disaster.
                # This deserves further investigation, maybe the
                # retry strategy can be pushed to u1db, or at least
                # it's something worthy to talk about with the
                # ubuntu folks.
                sync_tries -= 1
                continue
            except Exception as e:
                logger.exception("Unhandled error while syncing "
                                 "soledad: %r" % (e,))
                break

        # reached bottom, failed to sync
        # and there's nothing we can do...
        self.soledad_failed.emit()
        raise SoledadSyncError()

    def _try_soledad_init(self, uuid, secrets_path, local_db_path,
                          server_url, cert_file, auth_token):
        """
        Try to initialize soledad.

        :param uuid: user identifier
        :param secrets_path: path to secrets file
        :param local_db_path: path to local db file
        :param server_url: soledad server uri
        :param cert_file: path to the certificate of the ca used
                          to validate the SSL certificate used by the remote
                          soledad server.
        :type cert_file: str
        :param auth token: auth token
        :type auth_token: str
        """
        # TODO: If selected server fails, retry with another host
        # (issue #3309)
        encoding = sys.getfilesystemencoding()

        # XXX We should get a flag in soledad itself
        if flags.OFFLINE is True:
            Soledad._shared_db = MockSharedDB()
        try:
            self._soledad = Soledad(
                uuid,
                self._password,
                secrets_path=secrets_path.encode(encoding),
                local_db_path=local_db_path.encode(encoding),
                server_url=server_url,
                cert_file=cert_file.encode(encoding),
                auth_token=auth_token)

        # XXX All these errors should be handled by soledad itself,
        # and return a subclass of SoledadInitializationFailed

        # recoverable, will guarantee retries
        except socket.timeout:
            logger.debug("SOLEDAD initialization TIMED OUT...")
            self.soledad_timeout.emit()
            raise
        except socket.error as exc:
            logger.warning("Socket error while initializing soledad")
            self.soledad_timeout.emit()
            raise
        except BootstrapSequenceError as exc:
            logger.warning("Error while initializing soledad")
            self.soledad_timeout.emit()
            raise

        # unrecoverable
        except u1db_errors.Unauthorized:
            logger.error("Error while initializing soledad "
                         "(unauthorized).")
            self.soledad_failed.emit()
            raise
        except u1db_errors.HTTPError as exc:
            logger.exception("Error while initializing soledad "
                             "(HTTPError)")
            self.soledad_failed.emit()
            raise
        except Exception as exc:
            logger.exception("Unhandled error while initializating "
                             "soledad: %r" % (exc,))
            self.soledad_failed.emit()
            raise

    def _try_soledad_sync(self):
        """
        Try to sync soledad.
        Raises SoledadSyncError if not successful.
        """
        try:
            logger.debug("trying to sync soledad....")
            self._soledad.sync()
        except SSLError as exc:
            logger.error("%r" % (exc,))
            raise SoledadSyncError("Failed to sync soledad")
        except u1db_errors.InvalidGeneration as exc:
            logger.error("%r" % (exc,))
            raise SoledadSyncError("u1db: InvalidGeneration")
        except (sqlite_ProgrammingError, sqlcipher_ProgrammingError) as e:
            logger.exception("%r" % (e,))
            raise
        except Exception as exc:
            logger.exception("Unhandled error while syncing "
                             "soledad: %r" % (exc,))
            raise SoledadSyncError("Failed to sync soledad")

    def _download_config(self):
        """
        Download the Soledad config for the given provider
        """

        leap_assert(self._provider_config,
                    "We need a provider configuration!")
        logger.debug("Downloading Soledad config for %s" %
                     (self._provider_config.get_domain(),))

        self._soledad_config = SoledadConfig()
        download_service_config(
            self._provider_config,
            self._soledad_config,
            self._session,
            self._download_if_needed)

        # soledad config is ok, let's proceed to load and sync soledad
        # XXX but honestly, this is a pretty strange entry point for that.
        # it feels like it should be the other way around:
        # load_and_sync, and from there, if needed, call download_config

        uuid = self.srpauth.get_uuid()
        self.load_and_sync_soledad(uuid)

    def _get_gpg_bin_path(self):
        """
        Return the path to gpg binary.

        :returns: the gpg binary path
        :rtype: str
        """
        gpgbin = None
        if flags.STANDALONE:
            gpgbin = os.path.join(
                get_path_prefix(), "..", "apps", "mail", "gpg")
            if IS_WIN:
                gpgbin += ".exe"
        else:
            try:
                gpgbin_options = which("gpg")
                # gnupg checks that the path to the binary is not a
                # symlink, so we need to filter those and come up with
                # just one option.
                for opt in gpgbin_options:
                    if not os.path.islink(opt):
                        gpgbin = opt
                        break
            except IndexError as e:
                logger.debug("Couldn't find the gpg binary!")
                logger.exception(e)
        leap_check(gpgbin is not None, "Could not find gpg binary")
        return gpgbin

    def _init_keymanager(self, address, token):
        """
        Initialize the keymanager.

        :param address: the address to initialize the keymanager with.
        :type address: str
        :param token: the auth token for accessing webapp.
        :type token: str
        """
        srp_auth = self.srpauth
        logger.debug('initializing keymanager...')

        if flags.OFFLINE is True:
            args = (address, "https://localhost", self._soledad)
            kwargs = {
                "ca_cert_path": "",
                "api_uri": "",
                "api_version": "",
                "uid": self._uuid,
                "gpgbinary": self._get_gpg_bin_path()
            }
        else:
            args = (
                address,
                "https://nicknym.%s:6425" % (
                    self._provider_config.get_domain(),),
                self._soledad
            )
            kwargs = {
                "token": token,
                "ca_cert_path": self._provider_config.get_ca_cert_path(),
                "api_uri": self._provider_config.get_api_uri(),
                "api_version": self._provider_config.get_api_version(),
                "uid": srp_auth.get_uuid(),
                "gpgbinary": self._get_gpg_bin_path()
            }
        try:
            self._keymanager = KeyManager(*args, **kwargs)
        except KeyNotFound:
            logger.debug('key for %s not found.' % address)
        except Exception as exc:
            logger.exception(exc)
            raise

        if flags.OFFLINE is False:
            # make sure key is in server
            logger.debug('Trying to send key to server...')
            try:
                self._keymanager.send_key(openpgp.OpenPGPKey)
            except KeyNotFound:
                logger.debug('No key found for %s, will generate soon.'
                             % address)
            except Exception as exc:
                logger.error("Error sending key to server.")
                logger.exception(exc)
                # but we do not raise

    def _gen_key(self, _):
        """
        Generates the key pair if needed, uploads it to the webapp and
        nickserver
        """
        leap_assert(self._provider_config is not None,
                    "We need a provider configuration!")
        leap_assert(self._soledad is not None,
                    "We need a non-null soledad to generate keys")

        address = make_address(
            self._user, self._provider_config.get_domain())
        logger.debug("Retrieving key for %s" % (address,))

        try:
            self._keymanager.get_key(
                address, openpgp.OpenPGPKey, private=True, fetch_remote=False)
            return
        except KeyNotFound:
            logger.debug("Key not found. Generating key for %s" % (address,))

        # generate key
        try:
            self._keymanager.gen_key(openpgp.OpenPGPKey)
        except Exception as exc:
            logger.error("Error while generating key!")
            logger.exception(exc)
            raise

        # send key
        try:
            self._keymanager.send_key(openpgp.OpenPGPKey)
        except Exception as exc:
            logger.error("Error while sending key!")
            logger.exception(exc)
            raise

        logger.debug("Key generated successfully.")

    def run_soledad_setup_checks(self,
                                 provider_config,
                                 user,
                                 password,
                                 download_if_needed=False):
        """
        Starts the checks needed for a new soledad setup

        :param provider_config: Provider configuration
        :type provider_config: ProviderConfig
        :param user: User's login
        :type user: unicode
        :param password: User's password
        :type password: unicode
        :param download_if_needed: If True, it will only download
                                   files if the have changed since the
                                   time it was previously downloaded.
        :type download_if_needed: bool
        """
        leap_assert_type(provider_config, ProviderConfig)

        # XXX we should provider a method for setting provider_config
        self._provider_config = provider_config
        self._download_if_needed = download_if_needed
        self._user = user
        self._password = password

        cb_chain = [
            (self._download_config, self.download_config),
            (self._gen_key, self.gen_key)
        ]

        return self.addCallbackChain(cb_chain)
