# -*- coding: utf-8 -*-
# test_srpauth.py
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
Tests for:
    * leap/crypto/srpauth.py
"""
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os
import sys
import binascii
import requests
import mock

from mock import MagicMock
from nose.twistedtools import reactor, deferred
from twisted.python import log
from twisted.internet import threads
from functools import partial
from requests.models import Response
from simplejson.decoder import JSONDecodeError

from leap.common.testing.https_server import where
from leap.config.providerconfig import ProviderConfig
from leap.crypto import srpregister, srpauth
from leap.crypto.tests import fake_provider
from leap.util.request_helpers import get_content

log.startLogging(sys.stdout)


def _get_capath():
    return where("cacert.pem")

_here = os.path.split(__file__)[0]


class ImproperlyConfiguredError(Exception):
    """
    Raised if the test provider is missing configuration
    """


class SRPAuthTestCase(unittest.TestCase):
    """
    Tests for the SRPAuth class
    """
    __name__ = "SRPAuth tests"

    def setUp(self):
        """
        Sets up this TestCase with a simple and faked provider instance:

        * runs a threaded reactor
        * loads a mocked ProviderConfig that points to the certs in the
          leap.common.testing module.
        """
        factory = fake_provider.get_provider_factory()
        http = reactor.listenTCP(0, factory)
        https = reactor.listenSSL(
            0, factory,
            fake_provider.OpenSSLServerContextFactory())
        get_port = lambda p: p.getHost().port
        self.http_port = get_port(http)
        self.https_port = get_port(https)

        provider = ProviderConfig()
        provider.get_ca_cert_path = mock.create_autospec(
            provider.get_ca_cert_path)
        provider.get_ca_cert_path.return_value = _get_capath()

        provider.get_api_uri = mock.create_autospec(
            provider.get_api_uri)
        provider.get_api_uri.return_value = self._get_https_uri()

        loaded = provider.load(path=os.path.join(
            _here, "test_provider.json"))
        if not loaded:
            raise ImproperlyConfiguredError(
                "Could not load test provider config")
        self.register = srpregister.SRPRegister(provider_config=provider)
        self.provider = provider
        self.TEST_USER = "register_test_auth"
        self.TEST_PASS = "pass"

        # Reset the singleton
        srpauth.SRPAuth._SRPAuth__instance = None
        self.auth = srpauth.SRPAuth(self.provider)
        self.auth_backend = self.auth._SRPAuth__instance

        self.old_post = self.auth_backend._session.post
        self.old_put = self.auth_backend._session.put
        self.old_delete = self.auth_backend._session.delete

        self.old_start_auth = self.auth_backend._start_authentication
        self.old_proc_challenge = self.auth_backend._process_challenge
        self.old_extract_data = self.auth_backend._extract_data
        self.old_verify_session = self.auth_backend._verify_session
        self.old_auth_preproc = self.auth_backend._authentication_preprocessing
        self.old_get_sid = self.auth_backend.get_session_id
        self.old_cookie_get = self.auth_backend._session.cookies.get
        self.old_auth = self.auth_backend.authenticate

    def tearDown(self):
        self.auth_backend._session.post = self.old_post
        self.auth_backend._session.put = self.old_put
        self.auth_backend._session.delete = self.old_delete

        self.auth_backend._start_authentication = self.old_start_auth
        self.auth_backend._process_challenge = self.old_proc_challenge
        self.auth_backend._extract_data = self.old_extract_data
        self.auth_backend._verify_session = self.old_verify_session
        self.auth_backend._authentication_preprocessing = self.old_auth_preproc
        self.auth_backend.get_session_id = self.old_get_sid
        self.auth_backend._session.cookies.get = self.old_cookie_get
        self.auth_backend.authenticate = self.old_auth

    # helper methods

    def _get_https_uri(self):
        """
        Returns a https uri with the right https port initialized
        """
        return "https://localhost:%s" % (self.https_port,)

    # Auth tests

    def _prepare_auth_test(self, code=200, side_effect=None):
        """
        Creates the needed defers to test several test situations. It
        adds up to the auth preprocessing step.

        :param code: status code for the response of POST in requests
        :type code: int
        :param side_effect: side effect triggered by the POST method
                            in requests
        :type side_effect: some kind of Exception

        :returns: the defer that is created
        :rtype: defer.Deferred
        """
        res = Response()
        res.status_code = code
        self.auth_backend._session.post = mock.create_autospec(
            self.auth_backend._session.post,
            return_value=res,
            side_effect=side_effect)

        d = threads.deferToThread(self.register.register_user,
                                  self.TEST_USER,
                                  self.TEST_PASS)

        def wrapper_preproc(*args):
            return threads.deferToThread(
                self.auth_backend._authentication_preprocessing,
                self.TEST_USER, self.TEST_PASS)

        d.addCallback(wrapper_preproc)

        return d

    def test_safe_unhexlify(self):
        input_value = "somestring"
        test_value = binascii.hexlify(input_value)
        self.assertEqual(
            self.auth_backend._safe_unhexlify(test_value),
            input_value)

    def test_safe_unhexlify_not_raises(self):
        input_value = "somestring"
        test_value = binascii.hexlify(input_value)[:-1]

        with self.assertRaises(TypeError):
            binascii.unhexlify(test_value)

        self.auth_backend._safe_unhexlify(test_value)

    def test_preprocessing_loads_a(self):
        self.assertEqual(self.auth_backend._srp_a, None)
        self.auth_backend._authentication_preprocessing("user", "pass")
        self.assertIsNotNone(self.auth_backend._srp_a)
        self.assertTrue(len(self.auth_backend._srp_a) > 0)

    @deferred()
    def test_start_authentication(self):
        d = threads.deferToThread(self.register.register_user, self.TEST_USER,
                                  self.TEST_PASS)

        def wrapper_preproc(*args):
            return threads.deferToThread(
                self.auth_backend._authentication_preprocessing,
                self.TEST_USER, self.TEST_PASS)

        d.addCallback(wrapper_preproc)

        def wrapper(_):
            return threads.deferToThread(
                self.auth_backend._start_authentication,
                None, self.TEST_USER)

        d.addCallback(wrapper)
        return d

    @deferred()
    def test_start_authentication_fails_connerror(self):
        d = self._prepare_auth_test(
            side_effect=requests.exceptions.ConnectionError())

        def wrapper(_):
            with self.assertRaises(srpauth.SRPAuthConnectionError):
                self.auth_backend._start_authentication(None, self.TEST_USER)

        d.addCallback(partial(threads.deferToThread, wrapper))
        return d

    @deferred()
    def test_start_authentication_fails_any_error(self):
        d = self._prepare_auth_test(side_effect=Exception())

        def wrapper(_):
            with self.assertRaises(srpauth.SRPAuthenticationError):
                self.auth_backend._start_authentication(None, self.TEST_USER)

        d.addCallback(partial(threads.deferToThread, wrapper))
        return d

    @deferred()
    def test_start_authentication_fails_unknown_user(self):
        d = self._prepare_auth_test(422)

        def wrapper(_):
            with self.assertRaises(srpauth.SRPAuthUnknownUser):
                with mock.patch('leap.util.request_helpers.get_content',
                                new=mock.create_autospec(get_content)) as \
                        content:
                    content.return_value = ("{}", 0)

                    self.auth_backend._start_authentication(
                        None, self.TEST_USER)

        d.addCallback(partial(threads.deferToThread, wrapper))
        return d

    @deferred()
    def test_start_authentication_fails_errorcode(self):
        d = self._prepare_auth_test(302)

        def wrapper(_):
            with self.assertRaises(srpauth.SRPAuthBadStatusCode):
                with mock.patch('leap.util.request_helpers.get_content',
                                new=mock.create_autospec(get_content)) as \
                        content:
                    content.return_value = ("{}", 0)

                    self.auth_backend._start_authentication(None,
                                                            self.TEST_USER)

        d.addCallback(partial(threads.deferToThread, wrapper))
        return d

    @deferred()
    def test_start_authentication_fails_no_salt(self):
        d = self._prepare_auth_test(200)

        def wrapper(_):
            with self.assertRaises(srpauth.SRPAuthNoSalt):
                with mock.patch('leap.util.request_helpers.get_content',
                                new=mock.create_autospec(get_content)) as \
                        content:
                    content.return_value = ("{}", 0)

                    self.auth_backend._start_authentication(None,
                                                            self.TEST_USER)

        d.addCallback(partial(threads.deferToThread, wrapper))
        return d

    @deferred()
    def test_start_authentication_fails_no_B(self):
        d = self._prepare_auth_test(200)

        def wrapper(_):
            with self.assertRaises(srpauth.SRPAuthNoB):
                with mock.patch('leap.util.request_helpers.get_content',
                                new=mock.create_autospec(get_content)) as \
                        content:
                    content.return_value = ('{"salt": ""}', 0)

                    self.auth_backend._start_authentication(None,
                                                            self.TEST_USER)

        d.addCallback(partial(threads.deferToThread, wrapper))
        return d

    @deferred()
    def test_start_authentication_correct_saltb(self):
        d = self._prepare_auth_test(200)

        test_salt = "12345"
        test_B = "67890"

        def wrapper(_):
            with mock.patch('leap.util.request_helpers.get_content',
                            new=mock.create_autospec(get_content)) as \
                    content:
                content.return_value = ('{"salt":"%s", "B":"%s"}' % (test_salt,
                                                                     test_B),
                                        0)

                salt, B = self.auth_backend._start_authentication(
                    None,
                    self.TEST_USER)
                self.assertEqual(salt, test_salt)
                self.assertEqual(B, test_B)

        d.addCallback(partial(threads.deferToThread, wrapper))
        return d

    def _prepare_auth_challenge(self):
        """
        Creates the needed defers to test several test situations. It
        adds up to the start authentication step.

        :returns: the defer that is created
        :rtype: defer.Deferred
        """
        d = threads.deferToThread(self.register.register_user,
                                  self.TEST_USER,
                                  self.TEST_PASS)

        def wrapper_preproc(*args):
            return threads.deferToThread(
                self.auth_backend._authentication_preprocessing,
                self.TEST_USER, self.TEST_PASS)

        d.addCallback(wrapper_preproc)

        def wrapper_start(*args):
            return threads.deferToThread(
                self.auth_backend._start_authentication,
                None, self.TEST_USER)

        d.addCallback(wrapper_start)

        return d

    @deferred()
    def test_process_challenge_wrong_saltb(self):
        d = self._prepare_auth_challenge()

        def wrapper(salt_B):
            with self.assertRaises(srpauth.SRPAuthBadDataFromServer):
                self.auth_backend._process_challenge("",
                                                     username=self.TEST_USER)

        d.addCallback(partial(threads.deferToThread, wrapper))
        return d

    @deferred()
    def test_process_challenge_requests_problem_raises(self):
        d = self._prepare_auth_challenge()

        self.auth_backend._session.put = mock.create_autospec(
            self.auth_backend._session.put,
            side_effect=requests.exceptions.ConnectionError())

        def wrapper(salt_B):
            with self.assertRaises(srpauth.SRPAuthConnectionError):
                self.auth_backend._process_challenge(salt_B,
                                                     username=self.TEST_USER)

        d.addCallback(partial(threads.deferToThread, wrapper))

        return d

    @deferred()
    def test_process_challenge_json_decode_error(self):
        d = self._prepare_auth_challenge()

        def wrapper(salt_B):
            with mock.patch('leap.util.request_helpers.get_content',
                            new=mock.create_autospec(get_content)) as \
                    content:
                content.return_value = ("{", 0)
                content.side_effect = JSONDecodeError("", "", 0)

                with self.assertRaises(srpauth.SRPAuthJSONDecodeError):
                   self.auth_backend._process_challenge(
                       salt_B,
                       username=self.TEST_USER)

        d.addCallback(partial(threads.deferToThread, wrapper))

        return d

    @deferred()
    def test_process_challenge_bad_password(self):
        d = self._prepare_auth_challenge()

        res = Response()
        res.status_code = 422
        self.auth_backend._session.put = mock.create_autospec(
            self.auth_backend._session.put,
            return_value=res)

        def wrapper(salt_B):
            with mock.patch('leap.util.request_helpers.get_content',
                            new=mock.create_autospec(get_content)) as \
                    content:
                content.return_value = ("", 0)
                with self.assertRaises(srpauth.SRPAuthBadPassword):
                    self.auth_backend._process_challenge(
                        salt_B,
                        username=self.TEST_USER)

        d.addCallback(partial(threads.deferToThread, wrapper))

        return d

    @deferred()
    def test_process_challenge_bad_password2(self):
        d = self._prepare_auth_challenge()

        res = Response()
        res.status_code = 422
        self.auth_backend._session.put = mock.create_autospec(
            self.auth_backend._session.put,
            return_value=res)

        def wrapper(salt_B):
            with mock.patch('leap.util.request_helpers.get_content',
                            new=mock.create_autospec(get_content)) as \
                    content:
                content.return_value = ("[]", 0)
                with self.assertRaises(srpauth.SRPAuthBadPassword):
                    self.auth_backend._process_challenge(
                        salt_B,
                        username=self.TEST_USER)

        d.addCallback(partial(threads.deferToThread, wrapper))

        return d

    @deferred()
    def test_process_challenge_other_error_code(self):
        d = self._prepare_auth_challenge()

        res = Response()
        res.status_code = 300
        self.auth_backend._session.put = mock.create_autospec(
            self.auth_backend._session.put,
            return_value=res)

        def wrapper(salt_B):
            with mock.patch('leap.util.request_helpers.get_content',
                            new=mock.create_autospec(get_content)) as \
                    content:
                content.return_value = ("{}", 0)
                with self.assertRaises(srpauth.SRPAuthBadStatusCode):
                    self.auth_backend._process_challenge(
                        salt_B,
                        username=self.TEST_USER)

        d.addCallback(partial(threads.deferToThread, wrapper))

        return d

    @deferred()
    def test_process_challenge(self):
        d = self._prepare_auth_challenge()

        def wrapper(salt_B):
            self.auth_backend._process_challenge(salt_B,
                                                 username=self.TEST_USER)

        d.addCallback(partial(threads.deferToThread, wrapper))

        return d

    def test_extract_data_wrong_data(self):
        with self.assertRaises(srpauth.SRPAuthBadDataFromServer):
            self.auth_backend._extract_data(None)

        with self.assertRaises(srpauth.SRPAuthBadDataFromServer):
            self.auth_backend._extract_data("")

    def test_extract_data_fails_on_wrong_data_from_server(self):
        with self.assertRaises(srpauth.SRPAuthBadDataFromServer):
            self.auth_backend._extract_data({})

        with self.assertRaises(srpauth.SRPAuthBadDataFromServer):
            self.auth_backend._extract_data({"M2": ""})

    def test_extract_data_sets_uidtoken(self):
        test_uid = "someuid"
        test_m2 = "somem2"
        test_token = "sometoken"
        test_data = {
            "M2": test_m2,
            "id": test_uid,
            "token": test_token
        }
        m2 = self.auth_backend._extract_data(test_data)

        self.assertEqual(m2, test_m2)
        self.assertEqual(self.auth_backend.get_uid(), test_uid)
        self.assertEqual(self.auth_backend.get_uid(),
                         self.auth.get_uid())
        self.assertEqual(self.auth_backend.get_token(), test_token)
        self.assertEqual(self.auth_backend.get_token(),
                         self.auth.get_token())

    def _prepare_verify_session(self):
        """
        Prepares the tests for verify session with needed steps
        before. It adds up to the extract_data step.

        :returns: The defer to chain to
        :rtype: defer.Deferred
        """
        d = self._prepare_auth_challenge()

        def wrapper_proc_challenge(salt_B):
            return self.auth_backend._process_challenge(
                salt_B,
                username=self.TEST_USER)

        def wrapper_extract_data(data):
            return self.auth_backend._extract_data(data)

        d.addCallback(partial(threads.deferToThread, wrapper_proc_challenge))
        d.addCallback(partial(threads.deferToThread, wrapper_extract_data))

        return d

    @deferred()
    def test_verify_session_unhexlifiable_m2(self):
        d = self._prepare_verify_session()

        def wrapper(M2):
            with self.assertRaises(srpauth.SRPAuthBadDataFromServer):
                self.auth_backend._verify_session("za")  # unhexlifiable value

        d.addCallback(wrapper)

        return d

    @deferred()
    def test_verify_session_unverifiable_m2(self):
        d = self._prepare_verify_session()

        def wrapper(M2):
            with self.assertRaises(srpauth.SRPAuthVerificationFailed):
                # Correctly unhelifiable value, but not for verifying the
                # session
                self.auth_backend._verify_session("abc12")

        d.addCallback(wrapper)

        return d

    @deferred()
    def test_verify_session_fails_on_no_session_id(self):
        d = self._prepare_verify_session()

        def wrapper(M2):
            self.auth_backend._session.cookies.get = mock.create_autospec(
                self.auth_backend._session.cookies.get,
                return_value=None)
            with self.assertRaises(srpauth.SRPAuthNoSessionId):
                self.auth_backend._verify_session(M2)

        d.addCallback(wrapper)

        return d

    @deferred()
    def test_verify_session_session_id(self):
        d = self._prepare_verify_session()

        test_session_id = "12345"

        def wrapper(M2):
            self.auth_backend._session.cookies.get = mock.create_autospec(
                self.auth_backend._session.cookies.get,
                return_value=test_session_id)
            self.auth_backend._verify_session(M2)
            self.assertEqual(self.auth_backend.get_session_id(),
                             test_session_id)
            self.assertEqual(self.auth_backend.get_session_id(),
                             self.auth.get_session_id())

        d.addCallback(wrapper)

        return d

    @deferred()
    def test_verify_session(self):
        d = self._prepare_verify_session()

        def wrapper(M2):
            self.auth_backend._verify_session(M2)

        d.addCallback(wrapper)

        return d

    @deferred()
    def test_authenticate(self):
        self.auth_backend._authentication_preprocessing = mock.create_autospec(
            self.auth_backend._authentication_preprocessing,
            return_value=None)
        self.auth_backend._start_authentication = mock.create_autospec(
            self.auth_backend._start_authentication,
            return_value=None)
        self.auth_backend._process_challenge = mock.create_autospec(
            self.auth_backend._process_challenge,
            return_value=None)
        self.auth_backend._extract_data = mock.create_autospec(
            self.auth_backend._extract_data,
            return_value=None)
        self.auth_backend._verify_session = mock.create_autospec(
            self.auth_backend._verify_session,
            return_value=None)

        d = self.auth_backend.authenticate(self.TEST_USER, self.TEST_PASS)

        def check(*args):
            self.auth_backend._authentication_preprocessing.\
                assert_called_once_with(
                    username=self.TEST_USER,
                    password=self.TEST_PASS
                )
            self.auth_backend._start_authentication.assert_called_once_with(
                None,
                username=self.TEST_USER)
            self.auth_backend._process_challenge.assert_called_once_with(
                None,
                username=self.TEST_USER)
            self.auth_backend._extract_data.assert_called_once_with(
                None)
            self.auth_backend._verify_session.assert_called_once_with(None)

        d.addCallback(check)

        return d

    @deferred()
    def test_logout_fails_if_not_logged_in(self):

        def wrapper(*args):
            with self.assertRaises(AssertionError):
                self.auth_backend.logout()

        d = threads.deferToThread(wrapper)
        return d

    @deferred()
    def test_logout_traps_delete(self):
        self.auth_backend.get_session_id = mock.create_autospec(
            self.auth_backend.get_session_id,
            return_value="1234")
        self.auth_backend._session.delete = mock.create_autospec(
            self.auth_backend._session.delete,
            side_effect=Exception())

        def wrapper(*args):
            self.auth_backend.logout()

        d = threads.deferToThread(wrapper)
        return d

    @deferred()
    def test_logout_clears(self):
        self.auth_backend._session_id = "1234"

        def wrapper(*args):
            old_session = self.auth_backend._session
            self.auth_backend.logout()
            self.assertIsNone(self.auth_backend.get_session_id())
            self.assertIsNone(self.auth_backend.get_uid())
            self.assertNotEqual(old_session, self.auth_backend._session)

        d = threads.deferToThread(wrapper)
        return d


class SRPAuthSingletonTestCase(unittest.TestCase):
    def setUp(self):
        self.old_auth = srpauth.SRPAuth._SRPAuth__impl.authenticate

    def tearDown(self):
        srpauth.SRPAuth._SRPAuth__impl.authenticate = self.old_auth

    def test_singleton(self):
        obj1 = srpauth.SRPAuth(ProviderConfig())
        obj2 = srpauth.SRPAuth(ProviderConfig())
        self.assertEqual(obj1._SRPAuth__instance, obj2._SRPAuth__instance)

    @deferred()
    def test_authenticate_notifies_gui(self):
        auth = srpauth.SRPAuth(ProviderConfig())
        auth._SRPAuth__instance.authenticate = mock.create_autospec(
            auth._SRPAuth__instance.authenticate,
            return_value=threads.deferToThread(lambda: None))
        auth._gui_notify = mock.create_autospec(
            auth._gui_notify)

        d = auth.authenticate("", "")

        def check(*args):
            auth._gui_notify.assert_called_once_with(None)

        d.addCallback(check)
        return d

    @deferred()
    def test_authenticate_errsback(self):
        auth = srpauth.SRPAuth(ProviderConfig())
        auth._SRPAuth__instance.authenticate = mock.create_autospec(
            auth._SRPAuth__instance.authenticate,
            return_value=threads.deferToThread(MagicMock(
                side_effect=Exception())))
        auth._gui_notify = mock.create_autospec(
            auth._gui_notify)
        auth._errback = mock.create_autospec(
            auth._errback)

        d = auth.authenticate("", "")

        def check(*args):
            self.assertFalse(auth._gui_notify.called)
            self.assertEqual(auth._errback.call_count, 1)

        d.addCallback(check)
        return d

    @deferred()
    def test_authenticate_runs_cleanly_when_raises(self):
        auth = srpauth.SRPAuth(ProviderConfig())
        auth._SRPAuth__instance.authenticate = mock.create_autospec(
            auth._SRPAuth__instance.authenticate,
            return_value=threads.deferToThread(MagicMock(
                side_effect=Exception())))

        d = auth.authenticate("", "")

        return d

    @deferred()
    def test_authenticate_runs_cleanly(self):
        auth = srpauth.SRPAuth(ProviderConfig())
        auth._SRPAuth__instance.authenticate = mock.create_autospec(
            auth._SRPAuth__instance.authenticate,
            return_value=threads.deferToThread(MagicMock()))

        d = auth.authenticate("", "")

        return d

    def test_logout(self):
        auth = srpauth.SRPAuth(ProviderConfig())
        auth._SRPAuth__instance.logout = mock.create_autospec(
            auth._SRPAuth__instance.logout)

        self.assertTrue(auth.logout())

    def test_logout_rets_false_when_raises(self):
        auth = srpauth.SRPAuth(ProviderConfig())
        auth._SRPAuth__instance.logout = mock.create_autospec(
            auth._SRPAuth__instance.logout,
            side_effect=Exception())

        self.assertFalse(auth.logout())
