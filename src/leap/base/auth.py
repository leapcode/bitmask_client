import binascii
import logging

import requests
import srp

from leap.base import constants as baseconstants

logger = logging.getLogger(__name__)

SIGNUP_TIMEOUT = getattr(baseconstants, 'SIGNUP_TIMEOUT', 5)


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
