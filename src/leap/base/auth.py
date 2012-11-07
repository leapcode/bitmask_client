import binascii
import json
import logging
#import urlparse

import requests
import srp

from PyQt4 import QtCore

from leap.base import constants as baseconstants
from leap.crypto import leapkeyring

logger = logging.getLogger(__name__)

SIGNUP_TIMEOUT = getattr(baseconstants, 'SIGNUP_TIMEOUT', 5)

# XXX remove me!!
SERVER = "https://localhost:8443/1"


"""
Registration and authentication classes for the
SRP auth mechanism used in the leap platform.

We're currently using the (pure python?) srp library since
it seemed the fastest way of getting something working.

In the future we can switch to use python-gnutls, since
libgnutls implements srp protocol.
"""


class LeapSRPRegister(object):

    def __init__(self,
                 schema="https",
                 provider=None,
                 port=None,
                 register_path="1/users.json",
                 method="POST",
                 fetcher=requests,
                 srp=srp,
                 hashfun=srp.SHA256,
                 ng_constant=srp.NG_1024):

        self.schema = schema
        self.provider = provider
        self.port = port
        self.register_path = register_path
        self.method = method
        self.fetcher = fetcher
        self.srp = srp
        self.HASHFUN = hashfun
        self.NG = ng_constant

        self.init_session()

    def init_session(self):
        self.session = self.fetcher.session()

    def get_registration_uri(self):
        # XXX assert is https!
        # use urlparse
        if self.port:
            uri = "%s://%s:%s/%s" % (
                self.schema,
                self.provider,
                self.port,
                self.register_path)
        else:
            uri = "%s://%s/%s" % (
                self.schema,
                self.provider,
                self.register_path)

        return uri

    def register_user(self, username, password, keep=False):
        """
        @rtype: tuple
        @rparam: (ok, request)
        """
        salt, vkey = self.srp.create_salted_verification_key(
            username,
            password,
            self.HASHFUN,
            self.NG)

        user_data = {
            'user[login]': username,
            'user[password_verifier]': binascii.hexlify(vkey),
            'user[password_salt]': binascii.hexlify(salt)}

        uri = self.get_registration_uri()
        logger.debug('post to uri: %s' % uri)

        # XXX get self.method
        req = self.session.post(
            uri, data=user_data,
            timeout=SIGNUP_TIMEOUT)
        logger.debug(req)
        logger.debug('user_data: %s', user_data)
        #logger.debug('response: %s', req.text)
        # we catch it in the form
        #req.raise_for_status()
        return (req.ok, req)


class SRPAuthenticationError(Exception):
    """
    exception raised
    for authentication errors
    """
    pass

safe_unhexlify = lambda x: binascii.unhexlify(x) \
    if (len(x) % 2 == 0) else binascii.unhexlify('0' + x)


class SRPAuth(requests.auth.AuthBase):

    def __init__(self, username, password, verify=None):
        self.username = username
        self.password = password
        self.verify = verify

        # XXX init something similar to
        # SERVER...

        self.init_data = None
        self.session = requests.session()

        self.init_srp()

    def get_json_data(self, response):
        return json.loads(response.content)

    def init_srp(self):
        usr = srp.User(
            self.username,
            self.password,
            srp.SHA256,
            srp.NG_1024)
        uname, A = usr.start_authentication()

        self.srp_usr = usr
        self.A = A

    def get_auth_data(self):
        return {
            'login': self.username,
            'A': binascii.hexlify(self.A)
        }

    def get_init_data(self):
        try:
            init_session = self.session.post(
                SERVER + '/sessions.json/',
                data=self.get_auth_data(),
                verify=self.verify)
        except requests.exceptions.ConnectionError:
            raise SRPAuthenticationError(
                "No connection made (salt).")
        if init_session.status_code not in (200, ):
            raise SRPAuthenticationError(
                "No valid response (salt).")

        # XXX should  get auth_result.json instead
        self.init_data = self.get_json_data(init_session)
        return self.init_data

    def get_server_proof_data(self):
        try:
            auth_result = self.session.put(
                SERVER + '/sessions.json/' + self.username,
                data={'client_auth': binascii.hexlify(self.M)},
                verify=self.verify)
        except requests.exceptions.ConnectionError:
            raise SRPAuthenticationError(
                "No connection made (HAMK).")

        if auth_result.status_code not in (200, ):
            raise SRPAuthenticationError(
                "No valid response (HAMK).")

        # XXX should  get auth_result.json instead
        try:
            self.auth_data = self.get_json_data(auth_result)
        except ValueError:
            raise SRPAuthenticationError(
                "No valid data sent (HAMK)")

        return self.auth_data

    def authenticate(self):
        logger.debug('start authentication...')

        init_data = self.get_init_data()
        salt = init_data.get('salt', None)
        B = init_data.get('B', None)

        # XXX refactor this function
        # move checks and un-hex
        # to routines

        if not salt or not B:
            raise SRPAuthenticationError(
                "Server did not send initial data.")

        try:
            unhex_salt = safe_unhexlify(salt)
        except TypeError:
            raise SRPAuthenticationError(
                "Bad data from server (salt)")
        try:
            unhex_B = safe_unhexlify(B)
        except TypeError:
            raise SRPAuthenticationError(
                "Bad data from server (B)")

        self.M = self.srp_usr.process_challenge(
            unhex_salt,
            unhex_B
        )

        proof_data = self.get_server_proof_data()

        HAMK = proof_data.get("M2", None)
        if not HAMK:
            errors = proof_data.get('errors', None)
            if errors:
                logger.error(errors)
            raise SRPAuthenticationError("Server did not send HAMK.")

        try:
            unhex_HAMK = safe_unhexlify(HAMK)
        except TypeError:
            raise SRPAuthenticationError(
                "Bad data from server (HAMK)")

        self.srp_usr.verify_session(
            unhex_HAMK)

        try:
            assert self.srp_usr.authenticated()
            logger.debug('user is authenticated!')
        except (AssertionError):
            raise SRPAuthenticationError(
                "Auth verification failed.")

    def __call__(self, req):
        self.authenticate()
        req.session = self.session
        return req


def srpauth_protected(user=None, passwd=None, verify=True):
    """
    decorator factory that accepts
    user and password keyword arguments
    and add those to the decorated request
    """
    def srpauth(fn, user=user, passwd=passwd):
        def wrapper(*args, **kwargs):
            print 'uri is ', args[0]
            if user and passwd:
                auth = SRPAuth(user, passwd, verify)
                kwargs['auth'] = auth
            return fn(*args, **kwargs)
        return wrapper
    return srpauth


def get_leap_credentials():
    settings = QtCore.QSettings()
    full_username = settings.value('eip_username')
    username, domain = full_username.split('@')
    seed = settings.value('%s_seed' % domain, None)
    password = leapkeyring.leap_get_password(full_username, seed=seed)
    return (username, password)


# XXX TODO
# Pass verify as single argument,
# in srpauth_protected style

def magick_srpauth(fn):
    """
    decorator that gets user and password
    from the config file and adds those to
    the decorated request
    """
    logger.debug('magick srp auth decorator called')

    def wrapper(*args, **kwargs):
        #uri = args[0]
        # XXX Ugh!
        # Problem with this approach.
        # This won't work when we're using
        # api.foo.bar
        # Unless we keep a table with the
        # equivalencies...
        user, passwd = get_leap_credentials()
        auth = SRPAuth(user, passwd)
        kwargs['auth'] = auth
        return fn(*args, **kwargs)
    return wrapper


if __name__ == "__main__":
    import sys
    user = sys.argv[1]
    passwd = sys.argv[2]

    @srpauth_protected(user=user, passwd=passwd)
    def test_srp_protected_get(*args, **kwargs):
        req = requests.get(*args, **kwargs)
        req.raise_for_status
        #print req.content

    test_srp_protected_get('http://localhost:8443/1/cert')
