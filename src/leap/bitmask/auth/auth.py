import binascii
import logging
import os.path
import requests
import srp
import json
import re

from requests.adapters import HTTPAdapter

from leap.exceptions import (SRPAuthenticationError,
                             SRPAuthConnectionError,
                             SRPAuthBadStatusCode,
                             SRPAuthNoSalt,
                             SRPAuthNoB,
                             SRPAuthBadDataFromServer,
                             SRPAuthBadUserOrPassword,
                             SRPAuthVerificationFailed,
                             SRPAuthNoSessionId)

from leap.srp_session import SRPSession

logger = logging.getLogger(__name__)


class SRPAuth(object):

    def __init__(self, api_uri, verify_certificate=True, api_version=1):
        self.api_uri = api_uri
        self.api_version = api_version

        if verify_certificate is None:
            verify_certificate = True

        if isinstance(verify_certificate, (str, unicode)) and not os.path.isfile(verify_certificate):
            raise ValueError(
                'Path {0} is not a valid file'.format(verify_certificate))

        self.verify_certificate = verify_certificate

    def reset_session(self):
        adapter = HTTPAdapter(max_retries=50)
        self._session = requests.session()
        self._session.mount('https://', adapter)
        self.session_id = None

    def _authentication_preprocessing(self, username, password):

        logger.debug('Authentication preprocessing...')

        user = srp.User(username.encode('utf-8'),
                        password.encode('utf-8'),
                        srp.SHA256, srp.NG_1024)
        _, A = user.start_authentication()

        return user, A

    def _start_authentication(self, username, A):

        logger.debug('Starting authentication process...')
        try:
            auth_data = {
                'login': username,
                'A': binascii.hexlify(A)
            }
            sessions_url = '%s/%s/%s/' % \
                (self.api_uri,
                 self.api_version,
                 'sessions')

            verify_certificate = self.verify_certificate

            init_session = self._session.post(sessions_url,
                                              data=auth_data,
                                              verify=verify_certificate,
                                              timeout=30)
        except requests.exceptions.ConnectionError as e:
            logger.error('No connection made (salt): {0!r}'.format(e))
            raise SRPAuthConnectionError()
        except Exception as e:
            logger.error('Unknown error: %r' % (e,))
            raise SRPAuthenticationError()

        if init_session.status_code not in (200,):
            logger.error('No valid response (salt): '
                         'Status code = %r. Content: %r' %
                         (init_session.status_code, init_session.content))
            if init_session.status_code == 422:
                logger.error('Invalid username or password.')
                raise SRPAuthBadUserOrPassword()

            logger.error('There was a problem with authentication.')
            raise SRPAuthBadStatusCode()

        json_content = json.loads(init_session.content)
        salt = json_content.get('salt', None)
        B = json_content.get('B', None)

        if salt is None:
            logger.error('The server didn\'t send the salt parameter.')
            raise SRPAuthNoSalt()
        if B is None:
            logger.error('The server didn\'t send the B parameter.')
            raise SRPAuthNoB()

        return salt, B

    def _process_challenge(self, user, salt_B, username):
        logger.debug('Processing challenge...')
        try:
            salt, B = salt_B
            unhex_salt = _safe_unhexlify(salt)
            unhex_B = _safe_unhexlify(B)
        except (TypeError, ValueError) as e:
            logger.error('Bad data from server: %r' % (e,))
            raise SRPAuthBadDataFromServer()
        M = user.process_challenge(unhex_salt, unhex_B)

        auth_url = '%s/%s/%s/%s' % (self.api_uri,
                                    self.api_version,
                                    'sessions',
                                    username)

        auth_data = {
            'client_auth': binascii.hexlify(M)
        }

        try:
            auth_result = self._session.put(auth_url,
                                            data=auth_data,
                                            verify=self.verify_certificate,
                                            timeout=30)
        except requests.exceptions.ConnectionError as e:
            logger.error('No connection made (HAMK): %r' % (e,))
            raise SRPAuthConnectionError()

        if auth_result.status_code == 422:
            error = ''
            try:
                error = json.loads(auth_result.content).get('errors', '')
            except ValueError:
                logger.error('Problem parsing the received response: %s'
                             % (auth_result.content,))
            except AttributeError:
                logger.error('Expecting a dict but something else was '
                             'received: %s', (auth_result.content,))
            logger.error('[%s] Wrong password (HAMK): [%s]' %
                         (auth_result.status_code, error))
            raise SRPAuthBadUserOrPassword()

        if auth_result.status_code not in (200,):
            logger.error('No valid response (HAMK): '
                         'Status code = %s. Content = %r' %
                         (auth_result.status_code, auth_result.content))
            raise SRPAuthBadStatusCode()

        return json.loads(auth_result.content)

    def _extract_data(self, json_content):

        try:
            M2 = json_content.get('M2', None)
            uuid = json_content.get('id', None)
            token = json_content.get('token', None)
        except Exception as e:
            logger.error(e)
            raise SRPAuthBadDataFromServer()

        if M2 is None or uuid is None:
            logger.error('Something went wrong. Content = %r' %
                         (json_content,))
            raise SRPAuthBadDataFromServer()

        return uuid, token, M2

    def _verify_session(self, user, M2):

        logger.debug('Verifying session...')
        try:
            unhex_M2 = _safe_unhexlify(M2)
        except TypeError:
            logger.error('Bad data from server (HAMK)')
            raise SRPAuthBadDataFromServer()

        user.verify_session(unhex_M2)

        if not user.authenticated():
            logger.error('Auth verification failed.')
            raise SRPAuthVerificationFailed()
        logger.debug('Session verified.')

        session_id = self._session.cookies.get('_session_id', None)
        if not session_id:
            logger.error('Bad cookie from server (missing _session_id)')
            raise SRPAuthNoSessionId()

        logger.debug('SUCCESS LOGIN')
        return session_id

    def authenticate(self, username, password):

        self.reset_session()

        user, A = self._authentication_preprocessing(username, password)
        salt_B = self._start_authentication(username, A)

        json_content = self._process_challenge(user, salt_B, username)

        uuid, token, M2 = self._extract_data(json_content)
        session_id = self._verify_session(user, M2)

        self.session_id = session_id

        return SRPSession(username, token, uuid, session_id)

    def logout(self):
        logger.debug('Starting logout...')

        if self.session_id is None:
            logger.debug('Already logged out')
            return

        logout_url = '%s/%s/%s/' % (self.api_uri,
                                    self.api_version,
                                    'logout')
        try:
            self._session.delete(logout_url,
                                 data=self.session_id,
                                 verify=self.verify_certificate,
                                 timeout=30)
            self.reset_session()
        except Exception as e:
            logger.warning('Something went wrong with the logout: %r' %
                           (e,))
            raise
        else:
            logger.debug('Successfully logged out.')

    def change_password(self,
                        username,
                        current_password,
                        new_password,
                        token,
                        uuid):

        if self.session_id is None:
            logger.debug('Already logged out')
            return

        url = '%s/%s/users/%s.json' % (
            self.api_uri,
            self.api_version,
            uuid)

        salt, verifier = srp.create_salted_verification_key(
            username, new_password.encode('utf-8'),
            srp.SHA256, srp.NG_1024)

        cookies = {'_session_id': self.session_id}
        headers = {
            'Authorization':
            'Token token={0}'.format(token)
        }
        user_data = {
            'user[password_verifier]': binascii.hexlify(verifier),
            'user[password_salt]': binascii.hexlify(salt)
        }

        change_password = self._session.put(
            url, data=user_data,
            verify=self.verify_certificate,
            cookies=cookies,
            timeout=30,
            headers=headers)

        change_password.raise_for_status()

    def register(self, username, password):
        self.reset_session()

        username = username.encode('utf-8')
        password = password.encode('utf-8')

        validate_username(username)

        salt, verifier = srp.create_salted_verification_key(
            username,
            password,
            srp.SHA256,
            srp.NG_1024)

        user_data = {
            'user[login]': username,
            'user[password_verifier]': binascii.hexlify(verifier),
            'user[password_salt]': binascii.hexlify(salt)
        }

        url = "%s/%s/users" % (
            self.api_uri,
            self.api_version)

        logger.debug("Registering user: %s" % username)

        try:
            response = self._session.post(
                url,
                data=user_data,
                timeout=30,
                verify=self.verify_certificate)

        except requests.exceptions.RequestException as exc:
            logger.error(exc.message)
            raise

        if not response.ok:
            try:
                json_content = json.loads(response.content)
                error_msg = json_content.get("errors").get("login")[0]
                if not error_msg.istitle():
                    error_msg = "%s %s" % (username, error_msg)
                logger.error(error_msg)
            except Exception as e:
                logger.error("Unknown error: %s" % e.message)

        return response.ok


def _safe_unhexlify(val):
    return binascii.unhexlify(val) \
        if (len(val) % 2 == 0) else binascii.unhexlify('0' + val)


def validate_username(username):
    accepted_characters = '^[a-z0-9\-\_\.]*$'
    if not re.match(accepted_characters, username):
        raise ValueError('Only lowercase letters, digits, . - and _ allowed.')
