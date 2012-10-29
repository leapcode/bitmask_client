import cgi
import binascii
import json
import requests
import urlparse
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from mock import (patch, Mock)

#XXX should be moved to a general location
from leap.eip.tests.test_checks import NoLogRequestHandler

from leap.testing.basetest import BaseLeapTest
from BaseHTTPServer import BaseHTTPRequestHandler
from leap.testing.https_server import BaseHTTPSServerTestCase

from leap.base.auth import SRPAuth, SRPAuthenticationError

USERNAME = "0ACOJK"
PASSWORD = "WG3HD06E7ZF3"
INIT_DATA = {u'B': u'd74a9f592193bba8a818dcf500f412f60ce1b999aa9b5166f59fbe02aee97be9ec71a5d62fd16dedd973041efd4c7de0568c0d0c38a3806c78fc96f9ffa59dde89e5a04969905a83b8e700ee9c03b5636ad99624ed1514319b3bdac10cde498c8e064adf2fe04bfc5ee5df0dd06693961190a16caa182c090e59ac52feec693e',
              u'salt': u'd09ed33e'}
AUTH_RESULT = {u'M2': u'b040d0cd7ab1f93c4e87ffccdec07491782f2af303ad14f33dc4f0b4b2e40824'}
session_id = "'BAh7ByIPc2Vzc2lvbl9pZCIlNGU2ZGNhZDc4ZjNmMzE5YzRlMGUyNzJkMzBhYTA5ZTgiDHVzZXJfaWQiJWRhYzJmZGI4YTM5YmFjZGY4M2YyOWI4NDk2NTYzMDFl--6a322f6acb2f52b995bade4eaf54bd21820ab742"


class SRP_SERVER_HTTPSTests(BaseHTTPSServerTestCase, BaseLeapTest):
    class request_handler(NoLogRequestHandler, BaseHTTPRequestHandler):
        responses = {
            '/': ['OK', ''],
            '/1/sessions': [json.dumps(INIT_DATA)],
            '/1/sessions/' + USERNAME: [json.dumps(AUTH_RESULT)]
            }

        def do_GET(self):
            path = urlparse.urlparse(self.path)
            message = '\n'.join(self.responses.get(
                path.path, None))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(message)

        def do_PUT(self):
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD': 'PUT',
                        'CONTENT_TYPE': self.headers['Content-Type'],
                        })
            data = dict(
                (key, form[key].value) for key in form.keys())
            path = urlparse.urlparse(self.path)
            message = '\n'.join(
                self.responses.get(
                    path.path, ''))

            self.send_response(200)
            self.end_headers()
            self.wfile.write(message)

        def do_POST(self):
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD': 'POST',
                        'CONTENT_TYPE': self.headers['Content-Type'],
                        })
            data = dict(
                (key, form[key].value) for key in form.keys())
            path = urlparse.urlparse(self.path)
            message = '\n'.join(
                self.responses.get(
                    path.path, ''))

            self.send_response(200)
            self.end_headers()
            self.wfile.write(message)

    def test_srp_authenticate(self):
        srp_auth = SRPAuth(USERNAME, PASSWORD,
                "https://%s/1" % (self.get_server()), verify=False)

        # XXX We might want to raise different errors for SRP failures
        #This should fail at salt/B check time
        with patch.object(SRPAuth, "get_data") as mocked_post:
            with self.assertRaises(SRPAuthenticationError):
                mocked_post.return_value = json.loads("{}")
                srp_auth.authenticate()

        #This should fail at verification time
        with patch.object(SRPAuth, "get_data") as mocked_post:
            with self.assertRaises(SRPAuthenticationError):
                mocked_post.return_value = json.loads(
                            '{"salt":"%s", "B":"%s", "M2":"%s"}' %
                            (binascii.hexlify("fake"),
                             binascii.hexlify("sofake"),
                             binascii.hexlify("realfake")))
                srp_auth.authenticate()

        srp_auth.authenticate()


class SRP_Protected_URI_Sequence(BaseHTTPSServerTestCase, BaseLeapTest):
    class request_handler(NoLogRequestHandler, BaseHTTPRequestHandler):
        # XXX get the real URIs and find the server side auth sequence
        responses = {
            '/1/cert': '',
            '/1/get_protected': '',
            }

        def do_GET(self):
            path = urlparse.urlparse(self.path)
            message = '\n'.join(self.responses.get(
                path.path, None))
            self.send_response(200)
            if path.path == "/1/cert":
                self.send_header("set-cookie", "_session_id=" + session_id)
            if path.path == "/1/get_protected":
                # XXX use a cookie library to do some abstraction
                # and make this prettier
                if "cookie" in self.headers and \
                   self.headers["cookie"].find("_session_id") > -1:
                    self.send_header("set-cookie", "damn=right")
            self.end_headers()
            self.wfile.write(message)

    def test_srp_protected_uri(self):
        s = requests.session()
        r1 = s.get("https://%s/1/cert" %
                self.get_server(), verify=False)
        self.assertEquals(r1.cookies["_session_id"], session_id)
        r2 = s.get("https://%s/1/get_protected" %
                self.get_server(), verify=False)
        self.assertEquals(r2.cookies["damn"], 'right')
