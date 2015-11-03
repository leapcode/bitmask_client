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
import os
import socket
import sys

from sqlite3 import ProgrammingError as sqlite_ProgrammingError

from u1db import errors as u1db_errors
from twisted.internet import defer, reactor
from zope.proxy import sameProxiedObjects
from pysqlcipher.dbapi2 import ProgrammingError as sqlcipher_ProgrammingError

from leap.bitmask.config import flags
from leap.bitmask.config.providerconfig import ProviderConfig
from leap.bitmask.crypto.srpauth import SRPAuth
from leap.bitmask.logs.utils import get_logger
from leap.bitmask.services import download_service_config
from leap.bitmask.services.abstractbootstrapper import AbstractBootstrapper
from leap.bitmask.services.soledad.soledadconfig import SoledadConfig
from leap.bitmask.util import first, is_file, is_empty_file, make_address
from leap.bitmask.util import get_path_prefix
from leap.bitmask.util import here
from leap.bitmask.platform_init import IS_WIN, IS_MAC
from leap.common.check import leap_assert, leap_assert_type, leap_check
from leap.common.files import which
from leap.keymanager import KeyManager, openpgp
from leap.keymanager.errors import KeyNotFound
from leap.soledad.common.errors import InvalidAuthTokenError
from leap.soledad.client import Soledad
from leap.soledad.client.secrets import BootstrapSequenceError

logger = get_logger()

"""
These mocks are replicated from imap tests and the repair utility.
They are needed for the moment to knock out the remote capabilities of soledad
during the use of the offline mode.

They should not be needed after we allow a null remote initialization in the
soledad client, and a switch to remote sync-able mode during runtime.
"""


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

    def __init__(self, signaler=None):
        AbstractBootstrapper.__init__(self, signaler)

        if signaler is not None:
            self._cancel_signal = signaler.soledad_cancelled_bootstrap

        self._provider_config = None
        self._soledad_config = None
        self._download_if_needed = False

        self._user = ""
        self._password = u""
        self._address = ""
        self._uuid = ""

        self._srpauth = None

        self._soledad = None
        self._keymanager = None

    @property
    def srpauth(self):
        if flags.OFFLINE is True:
            return None
        if self._srpauth is None:
            leap_assert(self._provider_config is not None,
                        "We need a provider config")
            self._srpauth = SRPAuth(self._provider_config)
        return self._srpauth

    @property
    def soledad(self):
        return self._soledad

    @property
    def keymanager(self):
        return self._keymanager

    # initialization

    def load_offline_soledad(self, username, password, uuid):
        """
        Instantiate Soledad for offline use.

        :param username: full user id (user@provider)
        :type username: str or unicode
        :param password: the soledad passphrase
        :type password: unicode
        :param uuid: the user uuid
        :type uuid: str or unicode
        """
        self._address = username
        self._password = password
        self._uuid = uuid

        def error(failure):
            # TODO: we should handle more specific exceptions in here
            logger.exception(failure.value)
            self._signaler.signal(self._signaler.soledad_offline_failed)

        d = self.load_and_sync_soledad(uuid, offline=True)
        d.addCallback(
            lambda _: self._signaler.signal(
                self._signaler.soledad_offline_finished))
        d.addErrback(error)
        return d

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
        if offline is True:
            server_url = "http://localhost:9999/"
            cert_file = ""
        else:
            if uuid is None:
                uuid = self.srpauth.get_uuid()
            server_url = self._pick_server(uuid)
            cert_file = self._provider_config.get_ca_cert_path()

        return server_url, cert_file

    def _do_soledad_init(self, uuid, secrets_path, local_db_path,
                         server_url, cert_file, token, syncable):
        """
        Initialize soledad, retry if necessary and raise an exception if we
        can't succeed.

        :param uuid: user identifier
        :type uuid: str
        :param secrets_path: path to secrets file
        :type secrets_path: str
        :param local_db_path: path to local db file
        :type local_db_path: str
        :param server_url: soledad server uri
        :type server_url: str
        :param cert_file: path to the certificate of the ca used
                          to validate the SSL certificate used by the remote
                          soledad server.
        :type cert_file: str
        :param auth token: auth token
        :type auth_token: str
        """
        init_tries = 1
        while init_tries <= self.MAX_INIT_RETRIES:
            try:
                logger.debug("Trying to init soledad....")
                self._try_soledad_init(
                    uuid, secrets_path, local_db_path,
                    server_url, cert_file, token, syncable)
                logger.debug("Soledad has been initialized.")
                return
            except Exception as exc:
                init_tries += 1
                msg = "Init failed, retrying... (retry {0} of {1})".format(
                    init_tries, self.MAX_INIT_RETRIES)
                logger.warning(msg)
                continue

        self._signaler.signal(self._signaler.soledad_bootstrap_failed)
        logger.exception(exc)
        raise SoledadInitError()

    def load_and_sync_soledad(self, uuid=u"", offline=False):
        """
        Once everthing is in the right place, we instantiate and sync
        Soledad

        :param uuid: the uuid of the user, used in offline mode.
        :type uuid: unicode.
        :param offline: whether to instantiate soledad for offline use.
        :type offline: bool

        :return: A Deferred which fires when soledad is sync, or which fails
                 with SoledadInitError or SoledadSyncError
        :rtype: defer.Deferred
        """
        local_param = self._get_soledad_local_params(uuid, offline)
        remote_param = self._get_soledad_server_params(uuid, offline)

        secrets_path, local_db_path, token = local_param
        server_url, cert_file = remote_param

        if offline:
            return self._load_soledad_nosync(
                uuid, secrets_path, local_db_path, cert_file, token)

        else:
            return self._load_soledad_online(uuid, secrets_path, local_db_path,
                                             server_url, cert_file, token)

    def _load_soledad_online(self, uuid, secrets_path, local_db_path,
                             server_url, cert_file, token):
        syncable = True
        try:
            self._do_soledad_init(uuid, secrets_path, local_db_path,
                                  server_url, cert_file, token, syncable)
        except SoledadInitError as e:
            # re-raise the exceptions from try_init,
            # we're currently handling the retries from the
            # soledad-launcher in the gui.
            return defer.fail(e)

        leap_assert(not sameProxiedObjects(self._soledad, None),
                    "Null soledad, error while initializing")

        address = make_address(
            self._user, self._provider_config.get_domain())
        syncer = Syncer(self._soledad, self._signaler)

        d = self._init_keymanager(address, token)
        d.addCallback(lambda _: syncer.sync())
        d.addErrback(self._soledad_sync_errback)
        return d

    def _load_soledad_nosync(self, uuid, secrets_path, local_db_path,
                             cert_file, token):
        syncable = False
        self._do_soledad_init(uuid, secrets_path, local_db_path,
                              "", cert_file, token, syncable)
        d = self._init_keymanager(self._address, token)
        return d

    def _soledad_sync_errback(self, failure):
        failure.trap(InvalidAuthTokenError)
        # in the case of an invalid token we have already turned off mail and
        # warned the user

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

    def _try_soledad_init(self, uuid, secrets_path, local_db_path,
                          server_url, cert_file, auth_token, syncable):
        """
        Try to initialize soledad.

        :param uuid: user identifier
        :type uuid: str
        :param secrets_path: path to secrets file
        :type secrets_path: str
        :param local_db_path: path to local db file
        :type local_db_path: str
        :param server_url: soledad server uri
        :type server_url: str
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

        try:
            self._soledad = Soledad(
                uuid,
                self._password,
                secrets_path=secrets_path.encode(encoding),
                local_db_path=local_db_path.encode(encoding),
                server_url=server_url,
                cert_file=cert_file.encode(encoding),
                auth_token=auth_token,
                defer_encryption=True,
                syncable=syncable)

        # XXX All these errors should be handled by soledad itself,
        # and return a subclass of SoledadInitializationFailed

        # recoverable, will guarantee retries
        except (socket.timeout, socket.error, BootstrapSequenceError):
            logger.warning("Error while initializing Soledad")
            raise

        # unrecoverable
        except (u1db_errors.Unauthorized, u1db_errors.HTTPError):
            logger.error("Error while initializing Soledad (u1db error).")
            raise
        except Exception as exc:
            logger.exception("Unhandled error while initializating "
                             "Soledad: %r" % (exc,))
            raise

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
        if IS_MAC:
            gpgbin = os.path.abspath(
                os.path.join(here(), "apps", "mail", "gpg"))

        # During the transition towards gpg2, we can look for /usr/bin/gpg1
        # binary, in case it was renamed using dpkg-divert or manually.
        # We could just pick gpg2, but we need to solve #7564 first.
        if gpgbin is None:
            try:
                gpgbin_options = which("gpg1")
                for opt in gpgbin_options:
                    if not os.path.islink(opt):
                        gpgbin = opt
                        break
            except IndexError as e:
                logger.debug("Couldn't find the gpg1 binary!")
                logger.exception(e)
        leap_check(gpgbin is not None, "Could not find gpg1 binary")
        return gpgbin

    def _init_keymanager(self, address, token):
        """
        Initialize the keymanager.

        :param address: the address to initialize the keymanager with.
        :type address: str
        :param token: the auth token for accessing webapp.
        :type token: str
        :rtype: Deferred
        """
        logger.debug('initializing keymanager...')

        if flags.OFFLINE:
            nickserver_uri = "https://localhost"
            kwargs = {
                "ca_cert_path": "",
                "api_uri": "",
                "api_version": "",
                "uid": self._uuid,
                "gpgbinary": self._get_gpg_bin_path()
            }
        else:
            nickserver_uri = "https://nicknym.%s:6425" % (
                self._provider_config.get_domain(),)
            kwargs = {
                "token": token,
                "ca_cert_path": self._provider_config.get_ca_cert_path(),
                "api_uri": self._provider_config.get_api_uri(),
                "api_version": self._provider_config.get_api_version(),
                "uid": self.srpauth.get_uuid(),
                "gpgbinary": self._get_gpg_bin_path()
            }
        self._keymanager = KeyManager(address, nickserver_uri, self._soledad,
                                      **kwargs)

        if flags.OFFLINE is False:
            # make sure key is in server
            logger.debug('Trying to send key to server...')

            def send_errback(failure):
                if failure.check(KeyNotFound):
                    logger.debug(
                        'No key found for %s, it might be because soledad not '
                        'synced yet or it will generate it soon.' % address)
                else:
                    logger.error("Error sending key to server.")
                    logger.exception(failure.value)
                    # but we do not raise

            d = self._keymanager.send_key(openpgp.OpenPGPKey)
            d.addErrback(send_errback)
            return d
        else:
            return defer.succeed(None)

    def _gen_key(self):
        """
        Generates the key pair if needed, uploads it to the webapp and
        nickserver
        :rtype: Deferred
        """
        leap_assert(self._provider_config is not None,
                    "We need a provider configuration!")
        leap_assert(self._soledad is not None,
                    "We need a non-null soledad to generate keys")

        address = make_address(
            self._user, self._provider_config.get_domain())
        logger.debug("Retrieving key for %s" % (address,))

        def if_not_found_generate(failure):
            failure.trap(KeyNotFound)
            logger.debug("Key not found. Generating key for %s"
                         % (address,))
            d = self._keymanager.gen_key(openpgp.OpenPGPKey)
            d.addCallbacks(send_key, log_key_error("generating"))
            return d

        def send_key(_):
            d = self._keymanager.send_key(openpgp.OpenPGPKey)
            d.addCallbacks(
                lambda _: logger.debug("Key generated successfully."),
                log_key_error("sending"))

        def log_key_error(step):
            def log_err(failure):
                logger.error("Error while %s key!", (step,))
                logger.exception(failure.value)
                return failure
            return log_err

        d = self._keymanager.get_key(
            address, openpgp.OpenPGPKey, private=True, fetch_remote=False)
        d.addErrback(if_not_found_generate)
        return d

    def run_soledad_setup_checks(self, provider_config, user, password,
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

        :return: Deferred
        """
        leap_assert_type(provider_config, ProviderConfig)

        # XXX we should provider a method for setting provider_config
        self._provider_config = provider_config
        self._download_if_needed = download_if_needed
        self._user = user
        self._password = password

        if flags.OFFLINE:
            signal_finished = self._signaler.soledad_offline_finished
            self._signaler.signal(signal_finished)
            return defer.succeed(True)

        signal_finished = self._signaler.soledad_bootstrap_finished
        signal_failed = self._signaler.soledad_bootstrap_failed

        try:
            # XXX FIXME make this async too! (use txrequests)
            # Also, why the fuck would we want to download it *every time*?
            # We should be fine by using last-time config, or at least
            # trying it.
            self._download_config()
            uuid = self.srpauth.get_uuid()
        except Exception as e:
            # TODO: we should handle more specific exceptions in here
            self._soledad = None
            self._keymanager = None
            logger.exception("Error while bootstrapping Soledad: %r" % (e,))
            self._signaler.signal(signal_failed)
            return defer.succeed(None)

        # soledad config is ok, let's proceed to load and sync soledad
        d = self.load_and_sync_soledad(uuid)
        d.addCallback(lambda _: self._gen_key())
        d.addCallback(lambda _: self._signaler.signal(signal_finished))
        return d


class Syncer(object):
    """
    Takes care of retries, timeouts and other issues while syncing
    """
    # XXX: the timeout and proably all the stuff here should be moved to
    #      soledad

    MAX_SYNC_RETRIES = 10
    WAIT_MAX_SECONDS = 600

    def __init__(self, soledad, signaler):
        self._tries = 0
        self._soledad = soledad
        self._signaler = signaler

    def sync(self):
        self._callback_deferred = defer.Deferred()
        self._try_sync()
        return self._callback_deferred

    def _try_sync(self):
        logger.debug("BOOTSTRAPPER: trying to sync Soledad....")
        # pass defer_decryption=False to get inline decryption
        # for debugging.
        self._timeout_delayed_call = reactor.callLater(self.WAIT_MAX_SECONDS,
                                                       self._timeout)
        self._sync_deferred = self._soledad.sync(defer_decryption=True)
        self._sync_deferred.addCallbacks(self._success, self._error)

    def _success(self, result):
        logger.debug("Soledad has been synced!")
        self._timeout_delayed_call.cancel()
        self._callback_deferred.callback(result)
        # so long, and thanks for all the fish

    def _error(self, failure):
        self._timeout_delayed_call.cancel()
        if failure.check(InvalidAuthTokenError):
            logger.error('Invalid auth token while trying to sync Soledad')
            self._signaler.signal(
                self._signaler.soledad_invalid_auth_token)
            self._callback_deferred.fail(failure)
        elif failure.check(sqlite_ProgrammingError,
                           sqlcipher_ProgrammingError):
            logger.exception("%r" % (failure.value,))
            self._callback_deferred.fail(failure)
        else:
            logger.error("%r" % (failure.value,))
            self._retry()

    def _timeout(self):
        # maybe it's my connection, but I'm getting
        # ssl handshake timeouts and read errors quite often.
        # A particularly big sync is a disaster.
        # This deserves further investigation, maybe the
        # retry strategy can be pushed to u1db, or at least
        # it's something worthy to talk about with the
        # ubuntu folks.
        self._sync_deferred.cancel()
        self._retry()

    def _retry(self):
        self._tries += 1
        if self._tries < self.MAX_SYNC_RETRIES:
            msg = "Sync failed, retrying... (retry {0} of {1})".format(
                self._tries, self.MAX_SYNC_RETRIES)
            logger.warning(msg)
            self._try_sync()
        else:
            logger.error("Sync failed {0} times".format(self._tries))
            self._signaler.signal(self._signaler.soledad_bootstrap_failed)
            self._callback_deferred.errback(
                SoledadSyncError("Too many retries"))
