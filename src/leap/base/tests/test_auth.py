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

from leap.base.auth import SRPAuth

USERNAME = "0ACOJK"
PASSWORD = "WG3HD06E7ZF3"
INIT_DATA = {u'B': u'd74a9f592193bba8a818dcf500f412f60ce1b999aa9b5166f59fbe02aee97be9ec71a5d62fd16dedd973041efd4c7de0568c0d0c38a3806c78fc96f9ffa59dde89e5a04969905a83b8e700ee9c03b5636ad99624ed1514319b3bdac10cde498c8e064adf2fe04bfc5ee5df0dd06693961190a16caa182c090e59ac52feec693e',
              u'salt': u'd09ed33e'}
AUTH_RESULT = {u'M2': u'b040d0cd7ab1f93c4e87ffccdec07491782f2af303ad14f33dc4f0b4b2e40824'}


class SRP_SERVER_HTTPSTests(BaseHTTPSServerTestCase, BaseLeapTest):
    class request_handler(NoLogRequestHandler, BaseHTTPRequestHandler):
        responses = {
            '/': [ 'OK', '' ],
            '/1/sessions': [ json.dumps(INIT_DATA) ],
            '/1/sessions/' + USERNAME: [ json.dumps(AUTH_RESULT) ]
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

        srp_auth.authenticate()
