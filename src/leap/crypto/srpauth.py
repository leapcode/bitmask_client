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

import requests
import srp
import binascii
import logging

from PySide import QtCore, QtGui

from leap.config.providerconfig import ProviderConfig
from leap.util.check import leap_assert
from leap.util.checkerthread import CheckerThread

logger = logging.getLogger(__name__)


class SRPAuthenticationError(Exception):
    """
    Exception raised for authentication errors
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

        def __init__(self, provider_config):
            """
            Constructor for SRPAuth implementation

            @param server: Server to which we will authenticate
            @type server: str
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

            self._session = self._fetcher.session()
            self._session_id = None
            self._session_id_lock = QtCore.QMutex()
            self._uid = None
            self._uid_lock = QtCore.QMutex()

            self._srp_user = None
            self._srp_a = None

        def _safe_unhexlify(self, val):
            """
            Rounds the val to a multiple of 2 and returns the
            unhexlified value

            @param val: hexlified value
            @type val: str

            @rtype: binary hex data
            @return: unhexlified val
            """
            return binascii.unhexlify(val) \
                if (len(val) % 2 == 0) else binascii.unhexlify('0' + val)

        def _authentication_preprocessing(self, username, password):
            """
            Generates the SRP.User to get the A SRP parameter

            @param username: username to login
            @type username: str
            @param password: password for the username
            @type password: str
            """
            logger.debug("Authentication preprocessing...")
            self._srp_user = self._srp.User(username,
                                            password,
                                            self._hashfun,
                                            self._ng)
            _, A = self._srp_user.start_authentication()

            self._srp_a = A

        def _start_authentication(self, username, password):
            """
            Sends the first request for authentication to retrieve the
            salt and B parameter

            Might raise SRPAuthenticationError

            @param username: username to login
            @type username: str
            @param password: password for the username
            @type password: str

            @return: salt and B parameters
            @rtype: tuple
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
                                                  get_ca_cert_path())
            except requests.exceptions.ConnectionError as e:
                logger.error("No connection made (salt): %r" %
                             (e,))
                raise SRPAuthenticationError("Could not establish a "
                                             "connection")
            except Exception as e:
                logger.error("Unknown error: %r" % (e,))
                raise SRPAuthenticationError("Unknown error: %r" %
                                             (e,))

            if init_session.status_code not in (200,):
                logger.error("No valid response (salt): "
                             "Status code = %r. Content: %r" %
                             (init_session.status_code, init_session.content))
                if init_session.status_code == 422:
                    raise SRPAuthenticationError(self.tr("Unknown user"))
            salt = init_session.json().get("salt", None)
            B = init_session.json().get("B", None)

            if salt is None:
                logger.error("No salt parameter sent")
                raise SRPAuthenticationError(self.tr("The server did not send "
                                                     "the salt parameter"))
            if B is None:
                logger.error("No B parameter sent")
                raise SRPAuthenticationError(self.tr("The server did not send "
                                                     "the B parameter"))

            return salt, B

        def _process_challenge(self, salt, B, username):
            """
            Given the salt and B processes the auth challenge and
            generates the M2 parameter

            Might throw SRPAuthenticationError

            @param salt: salt for the username
            @type salt: str
            @param B: B SRP parameter
            @type B: str
            @param username: username for this session
            @type username: str

            @return: the M2 SRP parameter
            @rtype: str
            """
            logger.debug("Processing challenge...")
            try:
                unhex_salt = self._safe_unhexlify(salt)
                unhex_B = self._safe_unhexlify(B)
            except TypeError as e:
                logger.error("Bad data from server: %r" % (e,))
                raise SRPAuthenticationError(self.tr("The data sent from "
                                                     "the server had errors"))
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
                                                get_ca_cert_path())
            except requests.exceptions.ConnectionError as e:
                logger.error("No connection made (HAMK): %r" % (e,))
                raise SRPAuthenticationError(self.tr("Could not connect to "
                                                     "the server"))

            if auth_result.status_code == 422:
                logger.error("[%s] Wrong password (HAMK): [%s]" %
                             (auth_result.status_code,
                              auth_result.json().
                              get("errors", "")))
                raise SRPAuthenticationError(self.tr("Wrong password"))

            if auth_result.status_code not in (200,):
                logger.error("No valid response (HAMK): "
                             "Status code = %s. Content = %r" %
                             (auth_result.status_code, auth_result.content))
                raise SRPAuthenticationError(self.tr("Unknown error (%s)") %
                                             (auth_result.status_code,))

            M2 = auth_result.json().get("M2", None)
            self.set_uid(auth_result.json().get("id", None))

            if M2 is None or self.get_uid() is None:
                logger.error("Something went wrong. Content = %r" %
                             (auth_result.content,))
                raise SRPAuthenticationError(self.tr("Problem getting data "
                                                     "from server"))

            return M2

        def _verify_session(self, M2):
            """
            Verifies the session based on the M2 parameter. If the
            verification succeeds, it sets the session_id for this
            session

            Might throw SRPAuthenticationError

            @param M2: M2 SRP parameter
            @type M2: str
            """
            logger.debug("Verifying session...")
            try:
                unhex_M2 = self._safe_unhexlify(M2)
            except TypeError:
                logger.error("Bad data from server (HAWK)")
                raise SRPAuthenticationError(self.tr("Bad data from server"))

            self._srp_user.verify_session(unhex_M2)

            if not self._srp_user.authenticated():
                logger.error("Auth verification failed")
                raise SRPAuthenticationError(self.tr("Auth verification "
                                                     "failed"))
            logger.debug("Session verified.")

            self.set_session_id(self._session.cookies["_session_id"])

        def authenticate(self, username, password):
            """
            Executes the whole authentication process for a user

            Might raise SRPAuthenticationError

            @param username: username for this session
            @type username: str
            @param password: password for this user
            @type password: str
            """
            leap_assert(self.get_session_id() is None, "Already logged in")

            self._authentication_preprocessing(username, password)
            salt, B = self._start_authentication(username, password)
            M2 = self._process_challenge(salt, B, username)
            self._verify_session(M2)

            leap_assert(self.get_session_id(), "Something went wrong because"
                        " we don't have the auth cookie afterwards")

        def logout(self):
            """
            Logs out the current session.
            Expects a session_id to exists, might raise AssertionError
            """
            logger.debug("Starting logout...")

            leap_assert(self.get_session_id(),
                        "Cannot logout an unexisting session")

            logout_url = "%s/%s/%s/" % (self._provider_config.get_api_uri(),
                                        self._provider_config.
                                        get_api_version(),
                                        "sessions")
            try:
                self._session.delete(logout_url,
                                     data=self.get_session_id(),
                                     verify=self._provider_config.
                                     get_ca_cert_path())
            except Exception as e:
                logger.warning("Something went wrong with the logout: %r" %
                               (e,))

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

    __instance = None

    authentication_finished = QtCore.Signal(bool, str)
    logout_finished = QtCore.Signal(bool, str)

    DO_NOTHING = 0
    DO_LOGIN = 1
    DO_LOGOUT = 2

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

        self._should_login = self.DO_NOTHING
        self._should_login_lock = QtCore.QMutex()
        self._username = None
        self._password = None

    def authenticate(self, username, password):
        """
        Executes the whole authentication process for a user

        Might raise SRPAuthenticationError

        @param username: username for this session
        @type username: str
        @param password: password for this user
        @type password: str
        """

        try:
            self.__instance.authenticate(username, password)

            logger.debug("Successful login!")
            self.authentication_finished.emit(True, self.tr("Succeeded"))
            return True
        except Exception as e:
            logger.error("Error logging in %s" % (e,))
            self.authentication_finished.emit(False, "%s" % (e,))
        return False

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


if __name__ == "__main__":
    import sys
    from functools import partial
    app = QtGui.QApplication(sys.argv)

    import signal

    def sigint_handler(*args, **kwargs):
        logger.debug('SIGINT catched. shutting down...')
        checker = args[0]
        checker.set_should_quit()
        QtGui.QApplication.quit()

    def signal_tester(d):
        print d

    logger = logging.getLogger(name='leap')
    logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s '
        '- %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)

    checker = CheckerThread()

    sigint = partial(sigint_handler, checker)
    signal.signal(signal.SIGINT, sigint)

    timer = QtCore.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)
    app.connect(app, QtCore.SIGNAL("aboutToQuit()"),
                checker.set_should_quit)
    w = QtGui.QWidget()
    w.resize(100, 100)
    w.show()

    checker.start()

    provider = ProviderConfig()
    if provider.load("leap/providers/bitmask.net/provider.json"):
        # url = "%s/tickets" % (provider.get_api_uri(),)
        # print url
        # res = requests.session().get(url, verify=provider.get_ca_cert_path())
        # print res.content
        # res.raise_for_status()
        auth = SRPAuth(provider)
        auth_instantiated = partial(auth.authenticate, "test2", "sarasaaaa")

        checker.add_checks([auth_instantiated, auth.logout])

        #auth.authenticate("test2", "sarasaaaa")
        #res = requests.session().get("%s/cert" % (provider.get_api_uri(),),
                                     #verify=provider.get_ca_cert_path())
        #print res.content
        #auth.logout()

    sys.exit(app.exec_())
