#!/usr/bin/env python
"""A server faking some of the provider resources and apis,
used for testing Leap Client requests

It needs that you create a subfolder named 'certs',
and that you place the following files:

[ ] certs/leaptestscert.pem
[ ] certs/leaptestskey.pem
[ ] certs/cacert.pem
[ ] certs/openvpn.pem

[ ] provider.json
[ ] eip-service.json

"""
import binascii
import json
import os
import sys

# python SRP LIB (! important MUST be >=1.0.1 !)
import srp

# GnuTLS Example -- is not working as expected
from gnutls import crypto
from gnutls.constants import COMP_LZO, COMP_DEFLATE, COMP_NULL
from gnutls.interfaces.twisted import X509Credentials

# Going with OpenSSL as a workaround instead
# But we DO NOT want to introduce this dependency.
from OpenSSL import SSL

from zope.interface import Interface, Attribute, implements

from twisted.web.server import Site
from twisted.web.static import File
from twisted.web.resource import Resource
from twisted.internet import reactor

# See
# http://twistedmatrix.com/documents/current/web/howto/web-in-60/index.htmln
# for more examples

"""
Testing the FAKE_API:
#####################

 1) register an user
 >> curl -d "user[login]=me" -d "user[password_salt]=foo" -d "user[password_verifier]=beef" http://localhost:8000/1/users.json
 << {"errors": null}

 2) check that if you try to register again, it will fail:
 >> curl -d "user[login]=me" -d "user[password_salt]=foo" -d "user[password_verifier]=beef" http://localhost:8000/1/users.json
 << {"errors": {"login": "already taken!"}}

"""

# Globals to mock user/sessiondb

USERDB = {}
SESSIONDB = {}


safe_unhexlify = lambda x: binascii.unhexlify(x) \
    if (len(x) % 2 == 0) else binascii.unhexlify('0' + x)


class IUser(Interface):
    login = Attribute("User login.")
    salt = Attribute("Password salt.")
    verifier = Attribute("Password verifier.")
    session = Attribute("Session.")
    svr = Attribute("Server verifier.")


class User(object):
    implements(IUser)

    def __init__(self, login, salt, verifier):
        self.login = login
        self.salt = salt
        self.verifier = verifier
        self.session = None

    def set_server_verifier(self, svr):
        self.svr = svr

    def set_session(self, session):
        SESSIONDB[session] = self
        self.session = session


class FakeUsers(Resource):
    def __init__(self, name):
        self.name = name

    def render_POST(self, request):
        args = request.args

        login = args['user[login]'][0]
        salt = args['user[password_salt]'][0]
        verifier = args['user[password_verifier]'][0]

        if login in USERDB:
            return "%s\n" % json.dumps(
                {'errors': {'login': 'already taken!'}})

        print login, verifier, salt
        user = User(login, salt, verifier)
        USERDB[login] = user
        return json.dumps({'errors': None})


def get_user(request):
    login = request.args.get('login')
    if login:
        user = USERDB.get(login[0], None)
        if user:
            return user

    session = request.getSession()
    user = SESSIONDB.get(session, None)
    return user


class FakeSession(Resource):
    def __init__(self, name):
        self.name = name

    def render_GET(self, request):
        return "%s\n" % json.dumps({'errors': None})

    def render_POST(self, request):

        user = get_user(request)

        if not user:
            # XXX get real error from demo provider
            return json.dumps({'errors': 'no such user'})

        A = request.args['A'][0]

        _A = safe_unhexlify(A)
        _salt = safe_unhexlify(user.salt)
        _verifier = safe_unhexlify(user.verifier)

        svr = srp.Verifier(
            user.login,
            _salt,
            _verifier,
            _A,
            hash_alg=srp.SHA256,
            ng_type=srp.NG_1024)

        s, B = svr.get_challenge()

        _B = binascii.hexlify(B)

        print 'login = %s' % user.login
        print 'salt = %s' % user.salt
        print 'len(_salt) = %s' % len(_salt)
        print 'vkey = %s' % user.verifier
        print 'len(vkey) = %s' % len(_verifier)
        print 's = %s' % binascii.hexlify(s)
        print 'B = %s' % _B
        print 'len(B) = %s' % len(_B)

        session = request.getSession()
        user.set_session(session)
        user.set_server_verifier(svr)

        # yep, this is tricky.
        # some things are *already* unhexlified.
        data = {
            'salt': user.salt,
            'B': _B,
            'errors': None}

        return json.dumps(data)

    def render_PUT(self, request):

        # XXX check session???
        user = get_user(request)

        if not user:
            print 'NO USER'
            return json.dumps({'errors': 'no such user'})

        data = request.content.read()
        auth = data.split("client_auth=")
        M = auth[1] if len(auth) > 1 else None
        # if not H, return
        if not M:
            return json.dumps({'errors': 'no M proof passed by client'})

        svr = user.svr
        HAMK = svr.verify_session(binascii.unhexlify(M))
        if HAMK is None:
            print 'verification failed!!!'
            raise Exception("Authentication failed!")
            #import ipdb;ipdb.set_trace()

        assert svr.authenticated()
        print "***"
        print 'server authenticated user SRP!'
        print "***"

        return json.dumps(
            {'M2': binascii.hexlify(HAMK), 'errors': None})


class API_Sessions(Resource):
    def getChild(self, name, request):
        return FakeSession(name)


def get_certs_path():
    script_path = os.path.realpath(os.path.dirname(sys.argv[0]))
    certs_path = os.path.join(script_path, 'certs')
    return certs_path


def get_TLS_credentials():
    # XXX this is giving errors
    # XXX REview! We want to use gnutls!
    certs_path = get_certs_path()

    cert = crypto.X509Certificate(
        open(certs_path + '/leaptestscert.pem').read())
    key = crypto.X509PrivateKey(
        open(certs_path + '/leaptestskey.pem').read())
    ca = crypto.X509Certificate(
        open(certs_path + '/cacert.pem').read())
    #crl = crypto.X509CRL(open(certs_path + '/crl.pem').read())
    #cred = crypto.X509Credentials(cert, key, [ca], [crl])
    cred = X509Credentials(cert, key, [ca])
    cred.verify_peer = True
    cred.session_params.compressions = (COMP_LZO, COMP_DEFLATE, COMP_NULL)
    return cred


class OpenSSLServerContextFactory:
    # XXX workaround for broken TLS interface
    # from gnuTLS.

    def getContext(self):
        """Create an SSL context.
        This is a sample implementation that loads a certificate from a file
        called 'server.pem'."""
        certs_path = get_certs_path()

        ctx = SSL.Context(SSL.SSLv23_METHOD)
        ctx.use_certificate_file(certs_path + '/leaptestscert.pem')
        ctx.use_privatekey_file(certs_path + '/leaptestskey.pem')
        return ctx


if __name__ == "__main__":

    from twisted.python import log
    log.startLogging(sys.stdout)

    root = Resource()
    root.putChild("provider.json", File("./provider.json"))
    config = Resource()
    config.putChild(
        "eip-service.json",
        File("./eip-service.json"))
    apiv1 = Resource()
    apiv1.putChild("config", config)
    apiv1.putChild("sessions.json", API_Sessions())
    apiv1.putChild("users.json", FakeUsers(None))
    apiv1.putChild("cert", File(get_certs_path() + '/openvpn.pem'))
    root.putChild("1", apiv1)

    cred = get_TLS_credentials()

    factory = Site(root)

    # regular http (for debugging with curl)
    reactor.listenTCP(8000, factory)

    # TLS with gnutls --- seems broken :(
    #reactor.listenTLS(8003, factory, cred)

    # OpenSSL
    reactor.listenSSL(8443, factory, OpenSSLServerContextFactory())

    reactor.run()
