import binascii
import json
import logging
#import urlparse

import requests
import srp

from PyQt4 import QtCore

from leap.base import constants as baseconstants
from leap.crypto import leapkeyring
from leap.util.misc import null_check
from leap.util.web import get_https_domain_and_port

logger = logging.getLogger(__name__)

SIGNUP_TIMEOUT = getattr(baseconstants, 'SIGNUP_TIMEOUT', 5)

"""
Registration and authentication classes for the
SRP auth mechanism used in the leap platform.

We're using the srp library which uses a c-based implementation
of the protocol if the c extension is available, and a python-based
one if not.
"""


class SRPAuthenticationError(Exception):
    """
    exception raised
    for authentication errors
    """


safe_unhexlify = lambda x: binascii.unhexlify(x) \
    if (len(x) % 2 == 0) else binascii.unhexlify('0' + x)


class LeapSRPRegister(object):

    def __init__(self,
                 schema="https",
                 provider=None,
                 verify=True,
                 register_path="1/users",
                 method="POST",
                 fetcher=requests,
                 srp=srp,
                 hashfun=srp.SHA256,
                 ng_constant=srp.NG_1024):

        null_check(provider, "provider")

        self.schema = schema

        domain, port = get_https_domain_and_port(provider)
        self.provider = domain
        self.port = port

        self.verify = verify
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
            timeout=SIGNUP_TIMEOUT,
            verify=self.verify)
        # we catch it in the form
        #req.raise_for_status()
        return (req.ok, req)


class SRPAuth(requests.auth.AuthBase):

    def __init__(self, username, password, server=None, verify=None):
        # sanity check
        null_check(server, 'server')
        self.username = username
        self.password = password
        self.server = server
        self.verify = verify

        logger.debug('SRPAuth. verify=%s' % verify)
        logger.debug('server: %s. username=%s' % (server, username))

        self.init_data = None
        self.session = requests.session()

        self.init_srp()

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
                self.server + '/1/sessions/',
                data=self.get_auth_data(),
                verify=self.verify)
        except requests.exceptions.ConnectionError:
            raise SRPAuthenticationError(
                "No connection made (salt).")
        except:
            raise SRPAuthenticationError(
                "Unknown error (salt).")
        if init_session.status_code not in (200, ):
            raise SRPAuthenticationError(
                "No valid response (salt).")

        self.init_data = init_session.json
        return self.init_data

    def get_server_proof_data(self):
        try:
            auth_result = self.session.put(
                #self.server + '/1/sessions.json/' + self.username,
                self.server + '/1/sessions/' + self.username,
                data={'client_auth': binascii.hexlify(self.M)},
                verify=self.verify)
        except requests.exceptions.ConnectionError:
            raise SRPAuthenticationError(
                "No connection made (HAMK).")

        if auth_result.status_code not in (200, ):
            raise SRPAuthenticationError(
                "No valid response (HAMK).")

        self.auth_data = auth_result.json
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
        req.cookies = self.session.cookies
        return req


def srpauth_protected(user=None, passwd=None, server=None, verify=True):
    """
    decorator factory that accepts
    user and password keyword arguments
    and add those to the decorated request
    """
    def srpauth(fn):
        def wrapper(*args, **kwargs):
            if user and passwd:
                auth = SRPAuth(user, passwd, server, verify)
                kwargs['auth'] = auth
                kwargs['verify'] = verify
            if not args:
                logger.warning('attempting to get from empty uri!')
            return fn(*args, **kwargs)
        return wrapper
    return srpauth


def get_leap_credentials():
    settings = QtCore.QSettings()
    full_username = settings.value('username')
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

        # XXX pass verify and server too
        # (pop)
        auth = SRPAuth(user, passwd)
        kwargs['auth'] = auth
        return fn(*args, **kwargs)
    return wrapper


if __name__ == "__main__":
    """
    To test against test_provider (twisted version)
    Register an user: (will be valid during the session)
    >>> python auth.py add test password

    Test login with that user:
    >>> python auth.py login test password
    """

    import sys

    if len(sys.argv) not in (4, 5):
        print 'Usage: auth <add|login> <user> <pass> [server]'
        sys.exit(0)

    action = sys.argv[1]
    user = sys.argv[2]
    passwd = sys.argv[3]

    if len(sys.argv) == 5:
        SERVER = sys.argv[4]
    else:
        SERVER = "https://localhost:8443"

    if action == "login":

        @srpauth_protected(
            user=user, passwd=passwd, server=SERVER, verify=False)
        def test_srp_protected_get(*args, **kwargs):
            req = requests.get(*args, **kwargs)
            req.raise_for_status
            return req

        #req = test_srp_protected_get('https://localhost:8443/1/cert')
        req = test_srp_protected_get('%s/1/cert' % SERVER)
        #print 'cert :', req.content[:200] + "..."
        print req.content
        sys.exit(0)

    if action == "add":
        auth = LeapSRPRegister(provider=SERVER, verify=False)
        auth.register_user(user, passwd)
