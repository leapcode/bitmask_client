# Copyright 2011-2012 Canonical Ltd.
#
# This file is part of u1db.
#
# u1db is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# u1db is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with u1db.  If not, see <http://www.gnu.org/licenses/>.

"""Tests for HTTPDatabase"""

from oauth import oauth
try:
    import simplejson as json
except ImportError:
    import json  # noqa

from u1db import (
    errors,
    )

from leap.soledad.tests import u1db_tests as tests

from u1db.remote import (
    http_client,
    )


class TestEncoder(tests.TestCase):

    def test_encode_string(self):
        self.assertEqual("foo", http_client._encode_query_parameter("foo"))

    def test_encode_true(self):
        self.assertEqual("true", http_client._encode_query_parameter(True))

    def test_encode_false(self):
        self.assertEqual("false", http_client._encode_query_parameter(False))


class TestHTTPClientBase(tests.TestCaseWithServer):

    def setUp(self):
        super(TestHTTPClientBase, self).setUp()
        self.errors = 0

    def app(self, environ, start_response):
        if environ['PATH_INFO'].endswith('echo'):
            start_response("200 OK", [('Content-Type', 'application/json')])
            ret = {}
            for name in ('REQUEST_METHOD', 'PATH_INFO', 'QUERY_STRING'):
                ret[name] = environ[name]
            if environ['REQUEST_METHOD'] in ('PUT', 'POST'):
                ret['CONTENT_TYPE'] = environ['CONTENT_TYPE']
                content_length = int(environ['CONTENT_LENGTH'])
                ret['body'] = environ['wsgi.input'].read(content_length)
            return [json.dumps(ret)]
        elif environ['PATH_INFO'].endswith('error_then_accept'):
            if self.errors >= 3:
                start_response(
                    "200 OK", [('Content-Type', 'application/json')])
                ret = {}
                for name in ('REQUEST_METHOD', 'PATH_INFO', 'QUERY_STRING'):
                    ret[name] = environ[name]
                if environ['REQUEST_METHOD'] in ('PUT', 'POST'):
                    ret['CONTENT_TYPE'] = environ['CONTENT_TYPE']
                    content_length = int(environ['CONTENT_LENGTH'])
                    ret['body'] = '{"oki": "doki"}'
                return [json.dumps(ret)]
            self.errors += 1
            content_length = int(environ['CONTENT_LENGTH'])
            error = json.loads(
                environ['wsgi.input'].read(content_length))
            response = error['response']
            # In debug mode, wsgiref has an assertion that the status parameter
            # is a 'str' object. However error['status'] returns a unicode
            # object.
            status = str(error['status'])
            if isinstance(response, unicode):
                response = str(response)
            if isinstance(response, str):
                start_response(status, [('Content-Type', 'text/plain')])
                return [str(response)]
            else:
                start_response(status, [('Content-Type', 'application/json')])
                return [json.dumps(response)]
        elif environ['PATH_INFO'].endswith('error'):
            self.errors += 1
            content_length = int(environ['CONTENT_LENGTH'])
            error = json.loads(
                environ['wsgi.input'].read(content_length))
            response = error['response']
            # In debug mode, wsgiref has an assertion that the status parameter
            # is a 'str' object. However error['status'] returns a unicode
            # object.
            status = str(error['status'])
            if isinstance(response, unicode):
                response = str(response)
            if isinstance(response, str):
                start_response(status, [('Content-Type', 'text/plain')])
                return [str(response)]
            else:
                start_response(status, [('Content-Type', 'application/json')])
                return [json.dumps(response)]
        elif '/oauth' in environ['PATH_INFO']:
            base_url = self.getURL('').rstrip('/')
            oauth_req = oauth.OAuthRequest.from_request(
                http_method=environ['REQUEST_METHOD'],
                http_url=base_url + environ['PATH_INFO'],
                headers={'Authorization': environ['HTTP_AUTHORIZATION']},
                query_string=environ['QUERY_STRING']
            )
            oauth_server = oauth.OAuthServer(tests.testingOAuthStore)
            oauth_server.add_signature_method(tests.sign_meth_HMAC_SHA1)
            try:
                consumer, token, params = oauth_server.verify_request(
                    oauth_req)
            except oauth.OAuthError, e:
                start_response("401 Unauthorized",
                               [('Content-Type', 'application/json')])
                return [json.dumps({"error": "unauthorized",
                                          "message": e.message})]
            start_response("200 OK", [('Content-Type', 'application/json')])
            return [json.dumps([environ['PATH_INFO'], token.key, params])]

    def make_app(self):
        return self.app

    def getClient(self, **kwds):
        self.startServer()
        return http_client.HTTPClientBase(self.getURL('dbase'), **kwds)

    def test_construct(self):
        self.startServer()
        url = self.getURL()
        cli = http_client.HTTPClientBase(url)
        self.assertEqual(url, cli._url.geturl())
        self.assertIs(None, cli._conn)

    def test_parse_url(self):
        cli = http_client.HTTPClientBase(
                                     '%s://127.0.0.1:12345/' % self.url_scheme)
        self.assertEqual(self.url_scheme, cli._url.scheme)
        self.assertEqual('127.0.0.1', cli._url.hostname)
        self.assertEqual(12345, cli._url.port)
        self.assertEqual('/', cli._url.path)

    def test__ensure_connection(self):
        cli = self.getClient()
        self.assertIs(None, cli._conn)
        cli._ensure_connection()
        self.assertIsNot(None, cli._conn)
        conn = cli._conn
        cli._ensure_connection()
        self.assertIs(conn, cli._conn)

    def test_close(self):
        cli = self.getClient()
        cli._ensure_connection()
        cli.close()
        self.assertIs(None, cli._conn)

    def test__request(self):
        cli = self.getClient()
        res, headers = cli._request('PUT', ['echo'], {}, {})
        self.assertEqual({'CONTENT_TYPE': 'application/json',
                          'PATH_INFO': '/dbase/echo',
                          'QUERY_STRING': '',
                          'body': '{}',
                          'REQUEST_METHOD': 'PUT'}, json.loads(res))

        res, headers = cli._request('GET', ['doc', 'echo'], {'a': 1})
        self.assertEqual({'PATH_INFO': '/dbase/doc/echo',
                          'QUERY_STRING': 'a=1',
                          'REQUEST_METHOD': 'GET'}, json.loads(res))

        res, headers = cli._request('GET', ['doc', '%FFFF', 'echo'], {'a': 1})
        self.assertEqual({'PATH_INFO': '/dbase/doc/%FFFF/echo',
                          'QUERY_STRING': 'a=1',
                          'REQUEST_METHOD': 'GET'}, json.loads(res))

        res, headers = cli._request('POST', ['echo'], {'b': 2}, 'Body',
                                   'application/x-test')
        self.assertEqual({'CONTENT_TYPE': 'application/x-test',
                          'PATH_INFO': '/dbase/echo',
                          'QUERY_STRING': 'b=2',
                          'body': 'Body',
                          'REQUEST_METHOD': 'POST'}, json.loads(res))

    def test__request_json(self):
        cli = self.getClient()
        res, headers = cli._request_json(
            'POST', ['echo'], {'b': 2}, {'a': 'x'})
        self.assertEqual('application/json', headers['content-type'])
        self.assertEqual({'CONTENT_TYPE': 'application/json',
                          'PATH_INFO': '/dbase/echo',
                          'QUERY_STRING': 'b=2',
                          'body': '{"a": "x"}',
                          'REQUEST_METHOD': 'POST'}, res)

    def test_unspecified_http_error(self):
        cli = self.getClient()
        self.assertRaises(errors.HTTPError,
                          cli._request_json, 'POST', ['error'], {},
                          {'status': "500 Internal Error",
                           'response': "Crash."})
        try:
            cli._request_json('POST', ['error'], {},
                              {'status': "500 Internal Error",
                               'response': "Fail."})
        except errors.HTTPError, e:
            pass

        self.assertEqual(500, e.status)
        self.assertEqual("Fail.", e.message)
        self.assertTrue("content-type" in e.headers)

    def test_revision_conflict(self):
        cli = self.getClient()
        self.assertRaises(errors.RevisionConflict,
                          cli._request_json, 'POST', ['error'], {},
                          {'status': "409 Conflict",
                           'response': {"error": "revision conflict"}})

    def test_unavailable_proper(self):
        cli = self.getClient()
        cli._delays = (0, 0, 0, 0, 0)
        self.assertRaises(errors.Unavailable,
                          cli._request_json, 'POST', ['error'], {},
                          {'status': "503 Service Unavailable",
                           'response': {"error": "unavailable"}})
        self.assertEqual(5, self.errors)

    def test_unavailable_then_available(self):
        cli = self.getClient()
        cli._delays = (0, 0, 0, 0, 0)
        res, headers = cli._request_json(
            'POST', ['error_then_accept'], {'b': 2},
            {'status': "503 Service Unavailable",
             'response': {"error": "unavailable"}})
        self.assertEqual('application/json', headers['content-type'])
        self.assertEqual({'CONTENT_TYPE': 'application/json',
                          'PATH_INFO': '/dbase/error_then_accept',
                          'QUERY_STRING': 'b=2',
                          'body': '{"oki": "doki"}',
                          'REQUEST_METHOD': 'POST'}, res)
        self.assertEqual(3, self.errors)

    def test_unavailable_random_source(self):
        cli = self.getClient()
        cli._delays = (0, 0, 0, 0, 0)
        try:
            cli._request_json('POST', ['error'], {},
                              {'status': "503 Service Unavailable",
                               'response': "random unavailable."})
        except errors.Unavailable, e:
            pass

        self.assertEqual(503, e.status)
        self.assertEqual("random unavailable.", e.message)
        self.assertTrue("content-type" in e.headers)
        self.assertEqual(5, self.errors)

    def test_document_too_big(self):
        cli = self.getClient()
        self.assertRaises(errors.DocumentTooBig,
                          cli._request_json, 'POST', ['error'], {},
                          {'status': "403 Forbidden",
                           'response': {"error": "document too big"}})

    def test_user_quota_exceeded(self):
        cli = self.getClient()
        self.assertRaises(errors.UserQuotaExceeded,
                          cli._request_json, 'POST', ['error'], {},
                          {'status': "403 Forbidden",
                           'response': {"error": "user quota exceeded"}})

    def test_user_needs_subscription(self):
        cli = self.getClient()
        self.assertRaises(errors.SubscriptionNeeded,
                          cli._request_json, 'POST', ['error'], {},
                          {'status': "403 Forbidden",
                           'response': {"error": "user needs subscription"}})

    def test_generic_u1db_error(self):
        cli = self.getClient()
        self.assertRaises(errors.U1DBError,
                          cli._request_json, 'POST', ['error'], {},
                          {'status': "400 Bad Request",
                           'response': {"error": "error"}})
        try:
            cli._request_json('POST', ['error'], {},
                              {'status': "400 Bad Request",
                               'response': {"error": "error"}})
        except errors.U1DBError, e:
            pass
        self.assertIs(e.__class__, errors.U1DBError)

    def test_unspecified_bad_request(self):
        cli = self.getClient()
        self.assertRaises(errors.HTTPError,
                          cli._request_json, 'POST', ['error'], {},
                          {'status': "400 Bad Request",
                           'response': "<Bad Request>"})
        try:
            cli._request_json('POST', ['error'], {},
                              {'status': "400 Bad Request",
                               'response': "<Bad Request>"})
        except errors.HTTPError, e:
            pass

        self.assertEqual(400, e.status)
        self.assertEqual("<Bad Request>", e.message)
        self.assertTrue("content-type" in e.headers)

    def test_oauth(self):
        cli = self.getClient()
        cli.set_oauth_credentials(tests.consumer1.key, tests.consumer1.secret,
                                  tests.token1.key, tests.token1.secret)
        params = {'x': u'\xf0', 'y': "foo"}
        res, headers = cli._request('GET', ['doc', 'oauth'], params)
        self.assertEqual(
            ['/dbase/doc/oauth', tests.token1.key, params], json.loads(res))

        # oauth does its own internal quoting
        params = {'x': u'\xf0', 'y': "foo"}
        res, headers = cli._request('GET', ['doc', 'oauth', 'foo bar'], params)
        self.assertEqual(
            ['/dbase/doc/oauth/foo bar', tests.token1.key, params],
            json.loads(res))

    def test_oauth_ctr_creds(self):
        cli = self.getClient(creds={'oauth': {
            'consumer_key': tests.consumer1.key,
            'consumer_secret': tests.consumer1.secret,
            'token_key': tests.token1.key,
            'token_secret': tests.token1.secret,
            }})
        params = {'x': u'\xf0', 'y': "foo"}
        res, headers = cli._request('GET', ['doc', 'oauth'], params)
        self.assertEqual(
            ['/dbase/doc/oauth', tests.token1.key, params], json.loads(res))

    def test_unknown_creds(self):
        self.assertRaises(errors.UnknownAuthMethod,
                          self.getClient, creds={'foo': {}})
        self.assertRaises(errors.UnknownAuthMethod,
                          self.getClient, creds={})

    def test_oauth_Unauthorized(self):
        cli = self.getClient()
        cli.set_oauth_credentials(tests.consumer1.key, tests.consumer1.secret,
                                  tests.token1.key, "WRONG")
        params = {'y': 'foo'}
        self.assertRaises(errors.Unauthorized, cli._request, 'GET',
                          ['doc', 'oauth'], params)
