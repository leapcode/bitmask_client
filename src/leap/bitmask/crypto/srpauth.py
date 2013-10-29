# -*- coding: utf-8 -*-
# srpauth.py
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

import binascii
import logging

import requests
import srp
import json

#this error is raised from requests
from simplejson.decoder import JSONDecodeError
from functools import partial
from requests.adapters import HTTPAdapter

from PySide import QtCore
from twisted.internet import threads

from leap.bitmask.util import request_helpers as reqhelper
from leap.bitmask.util.compat import requests_has_max_retries
from leap.bitmask.util.constants import REQUEST_TIMEOUT
from leap.common.check import leap_assert
from leap.common.events import signal as events_signal
from leap.common.events import events_pb2 as proto

logger = logging.getLogger(__name__)


class SRPAuthenticationError(Exception):
    """
    Exception raised for authentication errors
    """
    pass


class SRPAuthConnectionError(SRPAuthenticationError):
    """
    Exception raised when there's a connection error
    """
    pass


class SRPAuthBadStatusCode(SRPAuthenticationError):
    """
    Exception raised when we received an unknown bad status code
    """
    pass


class SRPAuthNoSalt(SRPAuthenticationError):
    """
    Exception raised when we don't receive the salt param at a
    specific point in the auth process
    """
    pass


class SRPAuthNoB(SRPAuthenticationError):
    """
    Exception raised when we don't receive the B param at a specific
    point in the auth process
    """
    pass


class SRPAuthBadDataFromServer(SRPAuthenticationError):
    """
    Generic exception when we receive bad data from the server.
    """
    pass


class SRPAuthJSONDecodeError(SRPAuthenticationError):
    """
    Exception raised when there's a problem decoding the JSON content
    parsed as received from th e server.
    """
    pass


class SRPAuthBadUserOrPassword(SRPAuthenticationError):
    """
    Exception raised when the user provided a bad password to auth.
    """
    pass


class SRPAuthVerificationFailed(SRPAuthenticationError):
    """
    Exception raised when we can't verify the SRP data received from
    the server.
    """
    pass


class SRPAuthNoSessionId(SRPAuthenticationError):
    """
    Exception raised when we don't receive a session id from the
    server.
    """
    pass


class SRPAuth(QtCore.QObject):
    """
    SRPAuth singleton
    """

    class __impl(QtCore.QObject):
        """
        Implementation of the SRPAuth interface
        """

        LOGIN_KEY = "login"
        A_KEY = "A"
        CLIENT_AUTH_KEY = "client_auth"
        SESSION_ID_KEY = "_session_id"
        USER_VERIFIER_KEY = 'user[password_verifier]'
        USER_SALT_KEY = 'user[password_salt]'
        AUTHORIZATION_KEY = "Authorization"

        def __init__(self, provider_config):
            """
            Constructor for SRPAuth implementation

            :param server: Server to which we will authenticate
            :type server: str
            """
            QtCore.QObject.__init__(self)

            leap_assert(provider_config,
                        "We need a provider config to authenticate")

            self._provider_config = provider_config

            # **************************************************** #
            # Dependency injection helpers, override this for more
            # granular testing
            self._fetcher = requests
            self._srp = srp
            self._hashfun = self._srp.SHA256
            self._ng = self._srp.NG_1024
            # **************************************************** #

            self._reset_session()

            self._session_id = None
            self._session_id_lock = QtCore.QMutex()
            self._uid = None
            self._uid_lock = QtCore.QMutex()
            self._token = None
            self._token_lock = QtCore.QMutex()

            self._srp_user = None
            self._srp_a = None

            # Error msg displayed if the username or the password is invalid
            self._WRONG_USER_PASS = self.tr("Invalid username or password.")

            # User credentials stored for password changing checks
            self._username = None
            self._password = None

        def _reset_session(self):
            """
            Resets the current session and sets max retries to 30.
            """
            self._session = self._fetcher.session()
            # We need to bump the default retries, otherwise logout
            # fails most of the times
            # NOTE: This is a workaround for the moment, the server
            # side seems to return correctly every time, but it fails
            # on the client end.
            if requests_has_max_retries:
                adapter = HTTPAdapter(max_retries=30)
            else:
                adapter = HTTPAdapter()
            self._session.mount('https://', adapter)

        def _safe_unhexlify(self, val):
            """
            Rounds the val to a multiple of 2 and returns the
            unhexlified value

            :param val: hexlified value
            :type val: str

            :rtype: binary hex data
            :return: unhexlified val
            """
            return binascii.unhexlify(val) \
                if (len(val) % 2 == 0) else binascii.unhexlify('0' + val)

        def _authentication_preprocessing(self, username, password):
            """
            Generates the SRP.User to get the A SRP parameter

            :param username: username to login
            :type username: str
            :param password: password for the username
            :type password: str
            """
            logger.debug("Authentication preprocessing...")

            self._srp_user = self._srp.User(username,
                                            password,
                                            self._hashfun,
                                            self._ng)
            _, A = self._srp_user.start_authentication()

            self._srp_a = A

        def _start_authentication(self, _, username):
            """
            Sends the first request for authentication to retrieve the
            salt and B parameter

            Might raise all SRPAuthenticationError based:
              SRPAuthenticationError
              SRPAuthConnectionError
              SRPAuthBadStatusCode
              SRPAuthNoSalt
              SRPAuthNoB

            :param _: IGNORED, output from the previous callback (None)
            :type _: IGNORED
            :param username: username to login
            :type username: str

            :return: salt and B parameters
            :rtype: tuple
            """
            logger.debug("Starting authentication process...")
            try:
                auth_data = {
                    self.LOGIN_KEY: username,
                    self.A_KEY: binascii.hexlify(self._srp_a)
                }
                sessions_url = "%s/%s/%s/" % \
                    (self._provider_config.get_api_uri(),
                     self._provider_config.get_api_version(),
                     "sessions")
                init_session = self._session.post(sessions_url,
                                                  data=auth_data,
                                                  verify=self._provider_config.
                                                  get_ca_cert_path(),
                                                  timeout=REQUEST_TIMEOUT)
                # Clean up A value, we don't need it anymore
                self._srp_a = None
            except requests.exceptions.ConnectionError as e:
                logger.error("No connection made (salt): %r" %
                             (e,))
                raise SRPAuthConnectionError("Could not establish a "
                                             "connection")
            except Exception as e:
                logger.error("Unknown error: %r" % (e,))
                raise SRPAuthenticationError("Unknown error: %r" %
                                             (e,))

            content, mtime = reqhelper.get_content(init_session)

            if init_session.status_code not in (200,):
                logger.error("No valid response (salt): "
                             "Status code = %r. Content: %r" %
                             (init_session.status_code, content))
                if init_session.status_code == 422:
                    raise SRPAuthBadUserOrPassword(self._WRONG_USER_PASS)

                raise SRPAuthBadStatusCode(self.tr("There was a problem with"
                                                   " authentication"))

            json_content = json.loads(content)
            salt = json_content.get("salt", None)
            B = json_content.get("B", None)

            if salt is None:
                logger.error("No salt parameter sent")
                raise SRPAuthNoSalt(self.tr("The server did not send "
                                            "the salt parameter"))
            if B is None:
                logger.error("No B parameter sent")
                raise SRPAuthNoB(self.tr("The server did not send "
                                         "the B parameter"))

            return salt, B

        def _process_challenge(self, salt_B, username):
            """
            Given the salt and B processes the auth challenge and
            generates the M2 parameter

            Might raise SRPAuthenticationError based:
              SRPAuthenticationError
              SRPAuthBadDataFromServer
              SRPAuthConnectionError
              SRPAuthJSONDecodeError
              SRPAuthBadUserOrPassword

            :param salt_B: salt and B parameters for the username
            :type salt_B: tuple
            :param username: username for this session
            :type username: str

            :return: the M2 SRP parameter
            :rtype: str
            """
            logger.debug("Processing challenge...")
            try:
                salt, B = salt_B
                unhex_salt = self._safe_unhexlify(salt)
                unhex_B = self._safe_unhexlify(B)
            except (TypeError, ValueError) as e:
                logger.error("Bad data from server: %r" % (e,))
                raise SRPAuthBadDataFromServer(
                    self.tr("The data sent from the server had errors"))
            M = self._srp_user.process_challenge(unhex_salt, unhex_B)

            auth_url = "%s/%s/%s/%s" % (self._provider_config.get_api_uri(),
                                        self._provider_config.
                                        get_api_version(),
                                        "sessions",
                                        username)

            auth_data = {
                self.CLIENT_AUTH_KEY: binascii.hexlify(M)
            }

            try:
                auth_result = self._session.put(auth_url,
                                                data=auth_data,
                                                verify=self._provider_config.
                                                get_ca_cert_path(),
                                                timeout=REQUEST_TIMEOUT)
            except requests.exceptions.ConnectionError as e:
                logger.error("No connection made (HAMK): %r" % (e,))
                raise SRPAuthConnectionError(self.tr("Could not connect to "
                                                     "the server"))

            try:
                content, mtime = reqhelper.get_content(auth_result)
            except JSONDecodeError:
                raise SRPAuthJSONDecodeError("Bad JSON content in auth result")

            if auth_result.status_code == 422:
                error = ""
                try:
                    error = json.loads(content).get("errors", "")
                except ValueError:
                    logger.error("Problem parsing the received response: %s"
                                 % (content,))
                except AttributeError:
                    logger.error("Expecting a dict but something else was "
                                 "received: %s", (content,))
                logger.error("[%s] Wrong password (HAMK): [%s]" %
                             (auth_result.status_code, error))
                raise SRPAuthBadUserOrPassword(self._WRONG_USER_PASS)

            if auth_result.status_code not in (200,):
                logger.error("No valid response (HAMK): "
                             "Status code = %s. Content = %r" %
                             (auth_result.status_code, content))
                raise SRPAuthBadStatusCode(self.tr("Unknown error (%s)") %
                                           (auth_result.status_code,))

            return json.loads(content)

        def _extract_data(self, json_content):
            """
            Extracts the necessary parameters from json_content (M2,
            id, token)

            Might raise SRPAuthenticationError based:
              SRPBadDataFromServer

            :param json_content: Data received from the server
            :type json_content: dict
            """
            try:
                M2 = json_content.get("M2", None)
                uid = json_content.get("id", None)
                token = json_content.get("token", None)
            except Exception as e:
                logger.error(e)
                raise SRPAuthBadDataFromServer("Something went wrong with the "
                                               "login")

            self.set_uid(uid)
            self.set_token(token)

            if M2 is None or self.get_uid() is None:
                logger.error("Something went wrong. Content = %r" %
                             (json_content,))
                raise SRPAuthBadDataFromServer(self.tr("Problem getting data "
                                                       "from server"))

            events_signal(
                proto.CLIENT_UID, content=uid,
                reqcbk=lambda req, res: None)  # make the rpc call async

            return M2

        def _verify_session(self, M2):
            """
            Verifies the session based on the M2 parameter. If the
            verification succeeds, it sets the session_id for this
            session

            Might raise SRPAuthenticationError based:
              SRPAuthBadDataFromServer
              SRPAuthVerificationFailed

            :param M2: M2 SRP parameter
            :type M2: str
            """
            logger.debug("Verifying session...")
            try:
                unhex_M2 = self._safe_unhexlify(M2)
            except TypeError:
                logger.error("Bad data from server (HAWK)")
                raise SRPAuthBadDataFromServer(self.tr("Bad data from server"))

            self._srp_user.verify_session(unhex_M2)

            if not self._srp_user.authenticated():
                logger.error("Auth verification failed")
                raise SRPAuthVerificationFailed(self.tr("Auth verification "
                                                        "failed"))
            logger.debug("Session verified.")

            session_id = self._session.cookies.get(self.SESSION_ID_KEY, None)
            if not session_id:
                logger.error("Bad cookie from server (missing _session_id)")
                raise SRPAuthNoSessionId(self.tr("Session cookie "
                                                 "verification "
                                                 "failed"))

            events_signal(
                proto.CLIENT_SESSION_ID, content=session_id,
                reqcbk=lambda req, res: None)  # make the rpc call async

            self.set_session_id(session_id)

        def _threader(self, cb, res, *args, **kwargs):
            return threads.deferToThread(cb, res, *args, **kwargs)

        def change_password(self, current_password, new_password):
            """
            Changes the password for the currently logged user if the current
            password match.
            It requires to be authenticated.

            Might raise:
                SRPAuthBadUserOrPassword
                requests.exceptions.HTTPError

            :param current_password: the current password for the logged user.
            :type current_password: str
            :param new_password: the new password for the user
            :type new_password: str
            """
            leap_assert(self.get_uid() is not None)

            if current_password != self._password:
                raise SRPAuthBadUserOrPassword

            url = "%s/%s/users/%s.json" % (
                self._provider_config.get_api_uri(),
                self._provider_config.get_api_version(),
                self.get_uid())

            salt, verifier = self._srp.create_salted_verification_key(
                self._username, new_password, self._hashfun, self._ng)

            cookies = {self.SESSION_ID_KEY: self.get_session_id()}
            headers = {
                self.AUTHORIZATION_KEY:
                "Token token={0}".format(self.get_token())
            }
            user_data = {
                self.USER_VERIFIER_KEY: binascii.hexlify(verifier),
                self.USER_SALT_KEY: binascii.hexlify(salt)
            }

            change_password = self._session.put(
                url, data=user_data,
                verify=self._provider_config.get_ca_cert_path(),
                cookies=cookies,
                timeout=REQUEST_TIMEOUT,
                headers=headers)

            # In case of non 2xx it raises HTTPError
            change_password.raise_for_status()

            self._password = new_password

        def authenticate(self, username, password):
            """
            Executes the whole authentication process for a user

            Might raise SRPAuthenticationError

            :param username: username for this session
            :type username: str
            :param password: password for this user
            :type password: str

            :returns: A defer on a different thread
            :rtype: twisted.internet.defer.Deferred
            """
            leap_assert(self.get_session_id() is None, "Already logged in")

            # User credentials stored for password changing checks
            self._username = username
            self._password = password

            self._reset_session()

            d = threads.deferToThread(self._authentication_preprocessing,
                                      username=username,
                                      password=password)

            d.addCallback(
                partial(self._threader,
                        self._start_authentication),
                username=username)
            d.addCallback(
                partial(self._threader,
                        self._process_challenge),
                username=username)
            d.addCallback(
                partial(self._threader,
                        self._extract_data))
            d.addCallback(partial(self._threader,
                                  self._verify_session))

            return d

        def logout(self):
            """
            Logs out the current session.
            Expects a session_id to exists, might raise AssertionError
            """
            logger.debug("Starting logout...")

            if self.get_session_id() is None:
                logger.debug("Already logged out")
                return

            logout_url = "%s/%s/%s/" % (self._provider_config.get_api_uri(),
                                        self._provider_config.
                                        get_api_version(),
                                        "logout")
            try:
                self._session.delete(logout_url,
                                     data=self.get_session_id(),
                                     verify=self._provider_config.
                                     get_ca_cert_path(),
                                     timeout=REQUEST_TIMEOUT)
            except Exception as e:
                logger.warning("Something went wrong with the logout: %r" %
                               (e,))
                raise
            else:
                self.set_session_id(None)
                self.set_uid(None)
                # Also reset the session
                self._session = self._fetcher.session()
                logger.debug("Successfully logged out.")

        def set_session_id(self, session_id):
            QtCore.QMutexLocker(self._session_id_lock)
            self._session_id = session_id

        def get_session_id(self):
            QtCore.QMutexLocker(self._session_id_lock)
            return self._session_id

        def set_uid(self, uid):
            QtCore.QMutexLocker(self._uid_lock)
            self._uid = uid

        def get_uid(self):
            QtCore.QMutexLocker(self._uid_lock)
            return self._uid

        def set_token(self, token):
            QtCore.QMutexLocker(self._token_lock)
            self._token = token

        def get_token(self):
            QtCore.QMutexLocker(self._token_lock)
            return self._token

    __instance = None

    authentication_finished = QtCore.Signal(bool, str)
    logout_finished = QtCore.Signal(bool, str)

    def __init__(self, provider_config):
        """
        Creates a singleton instance if needed
        """
        QtCore.QObject.__init__(self)

        # Check whether we already have an instance
        if SRPAuth.__instance is None:
            # Create and remember instance
            SRPAuth.__instance = SRPAuth.__impl(provider_config)

        # Store instance reference as the only member in the handle
        self.__dict__['_SRPAuth__instance'] = SRPAuth.__instance

        # Generally, we initialize this with a provider_config once,
        # and after that initialize it without one and use the one
        # that was assigned before. But we need to update it if we
        # want to be able to logout and login into another provider.
        if provider_config is not None:
            SRPAuth.__instance._provider_config = provider_config

    def authenticate(self, username, password):
        """
        Executes the whole authentication process for a user

        Might raise SRPAuthenticationError based

        :param username: username for this session
        :type username: str
        :param password: password for this user
        :type password: str
        """
        username = username.lower()
        d = self.__instance.authenticate(username, password)
        d.addCallback(self._gui_notify)
        d.addErrback(self._errback)
        return d

    def change_password(self, current_password, new_password):
        """
        Changes the user's password.

        :param current_password: the current password of the user.
        :type current_password: str
        :param new_password: the new password for the user.
        :type new_password: str

        :returns: a defer to interact with.
        :rtype: twisted.internet.defer.Deferred
        """
        d = threads.deferToThread(
            self.__instance.change_password, current_password, new_password)
        return d

    def get_username(self):
        """
        Returns the username of the currently authenticated user or None if
        no user is logged.

        :rtype: str or None
        """
        if self.get_uid() is None:
            return None
        return self.__instance._username

    def _gui_notify(self, _):
        """
        Callback that notifies the UI with the proper signal.

        :param _: IGNORED, output from the previous callback (None)
        :type _: IGNORED
        """
        logger.debug("Successful login!")
        self.authentication_finished.emit(True, self.tr("Succeeded"))

    def _errback(self, failure):
        """
        General errback for the whole login process. Will notify the
        UI with the proper signal.

        :param failure: Failure object captured from a callback.
        :type failure: twisted.python.failure.Failure
        """
        logger.error("Error logging in %s" % (failure,))
        self.authentication_finished.emit(False, "%s" % (failure.value,))
        failure.trap(Exception)

    def get_session_id(self):
        return self.__instance.get_session_id()

    def get_uid(self):
        return self.__instance.get_uid()

    def get_token(self):
        return self.__instance.get_token()

    def logout(self):
        """
        Logs out the current session.
        Expects a session_id to exists, might raise AssertionError
        """
        try:
            self.__instance.logout()
            self.logout_finished.emit(True, self.tr("Succeeded"))
            return True
        except Exception as e:
            self.logout_finished.emit(False, "%s" % (e,))
        return False
