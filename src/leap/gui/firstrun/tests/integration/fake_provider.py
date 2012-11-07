#/usr/bin/env python
"""A server faking some of the provider resources and apis,
used for testing Leap Client requests.

Right needs that you create a subfolder named 'certs',
and that you place the following files:

[ ] certs/leaptestscert.pem
[ ] certs/leaptestskey.pem
[ ] certs/cacert.pem
[ ] certs/openvpn.pem

[ ] provider.json
[ ] eip-service.json

"""
import json
import os
import sys

# GnuTLS Example -- is not working as expected
from gnutls import crypto
from gnutls.constants import COMP_LZO, COMP_DEFLATE, COMP_NULL
from gnutls.interfaces.twisted import X509Credentials

# Going with OpenSSL as a workaround instead
# But we DO NOT want to introduce this dependency.
from OpenSSL import SSL

from twisted.web.server import Site
from twisted.web.static import File
from twisted.web.resource import Resource
from twisted.internet import reactor

# See
# http://twistedmatrix.com/documents/current/web/howto/web-in-60/index.htmln
# for more examples


class FakeSession(Resource):
    def __init__(self, name):
        self.name = name

    def render_GET(self, request):
        return json.dumps({'errors': None})

    def render_POST(self, request):
        return json.dumps(
            {'salt': 'deadbeef', 'B': 'deadbeef', 'errors': None})

    def render_PUT(self, request):
        return json.dumps(
            {'M2': 'deadbeef', 'errors': None})


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
    apiv1.putChild("cert", File(get_certs_path() + '/openvpn.pem'))
    root.putChild("1", apiv1)

    cred = get_TLS_credentials()

    factory = Site(root)

    # regular http
    reactor.listenTCP(8000, factory)

    # TLS with gnutls --- seems broken :(
    #reactor.listenTLS(8003, factory, cred)

    # OpenSSL
    reactor.listenSSL(8443, factory, OpenSSLServerContextFactory())

    reactor.run()
