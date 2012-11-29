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

"""Test the WSGI app."""

import paste.fixture
import sys
try:
    import simplejson as json
except ImportError:
    import json  # noqa
import StringIO

from u1db import (
    __version__ as _u1db_version,
    errors,
    sync,
    tests,
    )

from u1db.remote import (
    http_app,
    http_errors,
    )


class TestFencedReader(tests.TestCase):

    def test_init(self):
        reader = http_app._FencedReader(StringIO.StringIO(""), 25, 100)
        self.assertEqual(25, reader.remaining)

    def test_read_chunk(self):
        inp = StringIO.StringIO("abcdef")
        reader = http_app._FencedReader(inp, 5, 10)
        data = reader.read_chunk(2)
        self.assertEqual("ab", data)
        self.assertEqual(2, inp.tell())
        self.assertEqual(3, reader.remaining)

    def test_read_chunk_remaining(self):
        inp = StringIO.StringIO("abcdef")
        reader = http_app._FencedReader(inp, 4, 10)
        data = reader.read_chunk(9999)
        self.assertEqual("abcd", data)
        self.assertEqual(4, inp.tell())
        self.assertEqual(0, reader.remaining)

    def test_read_chunk_nothing_left(self):
        inp = StringIO.StringIO("abc")
        reader = http_app._FencedReader(inp, 2, 10)
        reader.read_chunk(2)
        self.assertEqual(2, inp.tell())
        self.assertEqual(0, reader.remaining)
        data = reader.read_chunk(2)
        self.assertEqual("", data)
        self.assertEqual(2, inp.tell())
        self.assertEqual(0, reader.remaining)

    def test_read_chunk_kept(self):
        inp = StringIO.StringIO("abcde")
        reader = http_app._FencedReader(inp, 4, 10)
        reader._kept = "xyz"
        data = reader.read_chunk(2)  # atmost ignored
        self.assertEqual("xyz", data)
        self.assertEqual(0, inp.tell())
        self.assertEqual(4, reader.remaining)
        self.assertIsNone(reader._kept)

    def test_getline(self):
        inp = StringIO.StringIO("abc\r\nde")
        reader = http_app._FencedReader(inp, 6, 10)
        reader.MAXCHUNK = 6
        line = reader.getline()
        self.assertEqual("abc\r\n", line)
        self.assertEqual("d", reader._kept)

    def test_getline_exact(self):
        inp = StringIO.StringIO("abcd\r\nef")
        reader = http_app._FencedReader(inp, 6, 10)
        reader.MAXCHUNK = 6
        line = reader.getline()
        self.assertEqual("abcd\r\n", line)
        self.assertIs(None, reader._kept)

    def test_getline_no_newline(self):
        inp = StringIO.StringIO("abcd")
        reader = http_app._FencedReader(inp, 4, 10)
        reader.MAXCHUNK = 6
        line = reader.getline()
        self.assertEqual("abcd", line)

    def test_getline_many_chunks(self):
        inp = StringIO.StringIO("abcde\r\nf")
        reader = http_app._FencedReader(inp, 8, 10)
        reader.MAXCHUNK = 4
        line = reader.getline()
        self.assertEqual("abcde\r\n", line)
        self.assertEqual("f", reader._kept)
        line = reader.getline()
        self.assertEqual("f", line)

    def test_getline_empty(self):
        inp = StringIO.StringIO("")
        reader = http_app._FencedReader(inp, 0, 10)
        reader.MAXCHUNK = 4
        line = reader.getline()
        self.assertEqual("", line)
        line = reader.getline()
        self.assertEqual("", line)

    def test_getline_just_newline(self):
        inp = StringIO.StringIO("\r\n")
        reader = http_app._FencedReader(inp, 2, 10)
        reader.MAXCHUNK = 4
        line = reader.getline()
        self.assertEqual("\r\n", line)
        line = reader.getline()
        self.assertEqual("", line)

    def test_getline_too_large(self):
        inp = StringIO.StringIO("x" * 50)
        reader = http_app._FencedReader(inp, 50, 25)
        reader.MAXCHUNK = 4
        self.assertRaises(http_app.BadRequest, reader.getline)

    def test_getline_too_large_complete(self):
        inp = StringIO.StringIO("x" * 25 + "\r\n")
        reader = http_app._FencedReader(inp, 50, 25)
        reader.MAXCHUNK = 4
        self.assertRaises(http_app.BadRequest, reader.getline)


class TestHTTPMethodDecorator(tests.TestCase):

    def test_args(self):
        @http_app.http_method()
        def f(self, a, b):
            return self, a, b
        res = f("self", {"a": "x", "b": "y"}, None)
        self.assertEqual(("self", "x", "y"), res)

    def test_args_missing(self):
        @http_app.http_method()
        def f(self, a, b):
            return a, b
        self.assertRaises(http_app.BadRequest, f, "self", {"a": "x"}, None)

    def test_args_unexpected(self):
        @http_app.http_method()
        def f(self, a):
            return a
        self.assertRaises(http_app.BadRequest, f, "self",
                                                  {"a": "x", "c": "z"}, None)

    def test_args_default(self):
        @http_app.http_method()
        def f(self, a, b="z"):
            return a, b
        res = f("self", {"a": "x"}, None)
        self.assertEqual(("x", "z"), res)

    def test_args_conversion(self):
        @http_app.http_method(b=int)
        def f(self, a, b):
            return self, a, b
        res = f("self", {"a": "x", "b": "2"}, None)
        self.assertEqual(("self", "x", 2), res)

        self.assertRaises(http_app.BadRequest, f, "self",
                                                  {"a": "x", "b": "foo"}, None)

    def test_args_conversion_with_default(self):
        @http_app.http_method(b=str)
        def f(self, a, b=None):
            return self, a, b
        res = f("self", {"a": "x"}, None)
        self.assertEqual(("self", "x", None), res)

    def test_args_content(self):
        @http_app.http_method()
        def f(self, a, content):
            return a, content
        res = f(self, {"a": "x"}, "CONTENT")
        self.assertEqual(("x", "CONTENT"), res)

    def test_args_content_as_args(self):
        @http_app.http_method(b=int, content_as_args=True)
        def f(self, a, b):
            return self, a, b
        res = f("self", {"a": "x"}, '{"b": "2"}')
        self.assertEqual(("self", "x", 2), res)

        self.assertRaises(http_app.BadRequest, f, "self", {}, 'not-json')

    def test_args_content_no_query(self):
        @http_app.http_method(no_query=True,
                              content_as_args=True)
        def f(self, a='a', b='b'):
            return a, b
        res = f("self", {}, '{"b": "y"}')
        self.assertEqual(('a', 'y'), res)

        self.assertRaises(http_app.BadRequest, f, "self", {'a': 'x'},
                          '{"b": "y"}')


class TestResource(object):

    @http_app.http_method()
    def get(self, a, b):
        self.args = dict(a=a, b=b)
        return 'Get'

    @http_app.http_method()
    def put(self, a, content):
        self.args = dict(a=a)
        self.content = content
        return 'Put'

    @http_app.http_method(content_as_args=True)
    def put_args(self, a, b):
        self.args = dict(a=a, b=b)
        self.order = ['a']
        self.entries = []

    @http_app.http_method()
    def put_stream_entry(self, content):
        self.entries.append(content)
        self.order.append('s')

    def put_end(self):
        self.order.append('e')
        return "Put/end"


class parameters:
    max_request_size = 200000
    max_entry_size = 100000


class TestHTTPInvocationByMethodWithBody(tests.TestCase):

    def test_get(self):
        resource = TestResource()
        environ = {'QUERY_STRING': 'a=1&b=2', 'REQUEST_METHOD': 'GET'}
        invoke = http_app.HTTPInvocationByMethodWithBody(resource, environ,
                                                         parameters)
        res = invoke()
        self.assertEqual('Get', res)
        self.assertEqual({'a': '1', 'b': '2'}, resource.args)

    def test_put_json(self):
        resource = TestResource()
        body = '{"body": true}'
        environ = {'QUERY_STRING': 'a=1', 'REQUEST_METHOD': 'PUT',
                   'wsgi.input': StringIO.StringIO(body),
                   'CONTENT_LENGTH': str(len(body)),
                   'CONTENT_TYPE': 'application/json'}
        invoke = http_app.HTTPInvocationByMethodWithBody(resource, environ,
                                                         parameters)
        res = invoke()
        self.assertEqual('Put', res)
        self.assertEqual({'a': '1'}, resource.args)
        self.assertEqual('{"body": true}', resource.content)

    def test_put_sync_stream(self):
        resource = TestResource()
        body = (
            '[\r\n'
            '{"b": 2},\r\n'        # args
            '{"entry": "x"},\r\n'  # stream entry
            '{"entry": "y"}\r\n'   # stream entry
            ']'
            )
        environ = {'QUERY_STRING': 'a=1', 'REQUEST_METHOD': 'PUT',
                   'wsgi.input': StringIO.StringIO(body),
                   'CONTENT_LENGTH': str(len(body)),
                   'CONTENT_TYPE': 'application/x-u1db-sync-stream'}
        invoke = http_app.HTTPInvocationByMethodWithBody(resource, environ,
                                                         parameters)
        res = invoke()
        self.assertEqual('Put/end', res)
        self.assertEqual({'a': '1', 'b': 2}, resource.args)
        self.assertEqual(
            ['{"entry": "x"}', '{"entry": "y"}'], resource.entries)
        self.assertEqual(['a', 's', 's', 'e'], resource.order)

    def _put_sync_stream(self, body):
        resource = TestResource()
        environ = {'QUERY_STRING': 'a=1&b=2', 'REQUEST_METHOD': 'PUT',
                   'wsgi.input': StringIO.StringIO(body),
                   'CONTENT_LENGTH': str(len(body)),
                   'CONTENT_TYPE': 'application/x-u1db-sync-stream'}
        invoke = http_app.HTTPInvocationByMethodWithBody(resource, environ,
                                                         parameters)
        invoke()

    def test_put_sync_stream_wrong_start(self):
        self.assertRaises(http_app.BadRequest,
                          self._put_sync_stream, "{}\r\n]")

        self.assertRaises(http_app.BadRequest,
                          self._put_sync_stream, "\r\n{}\r\n]")

        self.assertRaises(http_app.BadRequest,
                          self._put_sync_stream, "")

    def test_put_sync_stream_wrong_end(self):
        self.assertRaises(http_app.BadRequest,
                          self._put_sync_stream, "[\r\n{}")

        self.assertRaises(http_app.BadRequest,
                          self._put_sync_stream, "[\r\n")

        self.assertRaises(http_app.BadRequest,
                          self._put_sync_stream, "[\r\n{}\r\n]\r\n...")

    def test_put_sync_stream_missing_comma(self):
        self.assertRaises(http_app.BadRequest,
                          self._put_sync_stream, "[\r\n{}\r\n{}\r\n]")

    def test_put_sync_stream_extra_comma(self):
        self.assertRaises(http_app.BadRequest,
                          self._put_sync_stream, "[\r\n{},\r\n]")

        self.assertRaises(http_app.BadRequest,
                          self._put_sync_stream, "[\r\n{},\r\n{},\r\n]")

    def test_bad_request_decode_failure(self):
        resource = TestResource()
        environ = {'QUERY_STRING': 'a=\xff', 'REQUEST_METHOD': 'PUT',
                   'wsgi.input': StringIO.StringIO('{}'),
                   'CONTENT_LENGTH': '2',
                   'CONTENT_TYPE': 'application/json'}
        invoke = http_app.HTTPInvocationByMethodWithBody(resource, environ,
                                                         parameters)
        self.assertRaises(http_app.BadRequest, invoke)

    def test_bad_request_unsupported_content_type(self):
        resource = TestResource()
        environ = {'QUERY_STRING': '', 'REQUEST_METHOD': 'PUT',
                   'wsgi.input': StringIO.StringIO('{}'),
                   'CONTENT_LENGTH': '2',
                   'CONTENT_TYPE': 'text/plain'}
        invoke = http_app.HTTPInvocationByMethodWithBody(resource, environ,
                                                         parameters)
        self.assertRaises(http_app.BadRequest, invoke)

    def test_bad_request_content_length_too_large(self):
        resource = TestResource()
        environ = {'QUERY_STRING': '', 'REQUEST_METHOD': 'PUT',
                   'wsgi.input': StringIO.StringIO('{}'),
                   'CONTENT_LENGTH': '10000',
                   'CONTENT_TYPE': 'text/plain'}

        resource.max_request_size = 5000
        resource.max_entry_size = sys.maxint  # we don't get to use this

        invoke = http_app.HTTPInvocationByMethodWithBody(resource, environ,
                                                         parameters)
        self.assertRaises(http_app.BadRequest, invoke)

    def test_bad_request_no_content_length(self):
        resource = TestResource()
        environ = {'QUERY_STRING': '', 'REQUEST_METHOD': 'PUT',
                   'wsgi.input': StringIO.StringIO('a'),
                   'CONTENT_TYPE': 'application/json'}
        invoke = http_app.HTTPInvocationByMethodWithBody(resource, environ,
                                                         parameters)
        self.assertRaises(http_app.BadRequest, invoke)

    def test_bad_request_invalid_content_length(self):
        resource = TestResource()
        environ = {'QUERY_STRING': '', 'REQUEST_METHOD': 'PUT',
                   'wsgi.input': StringIO.StringIO('abc'),
                   'CONTENT_LENGTH': '1unk',
                   'CONTENT_TYPE': 'application/json'}
        invoke = http_app.HTTPInvocationByMethodWithBody(resource, environ,
                                                         parameters)
        self.assertRaises(http_app.BadRequest, invoke)

    def test_bad_request_empty_body(self):
        resource = TestResource()
        environ = {'QUERY_STRING': '', 'REQUEST_METHOD': 'PUT',
                   'wsgi.input': StringIO.StringIO(''),
                   'CONTENT_LENGTH': '0',
                   'CONTENT_TYPE': 'application/json'}
        invoke = http_app.HTTPInvocationByMethodWithBody(resource, environ,
                                                         parameters)
        self.assertRaises(http_app.BadRequest, invoke)

    def test_bad_request_unsupported_method_get_like(self):
        resource = TestResource()
        environ = {'QUERY_STRING': '', 'REQUEST_METHOD': 'DELETE'}
        invoke = http_app.HTTPInvocationByMethodWithBody(resource, environ,
                                                         parameters)
        self.assertRaises(http_app.BadRequest, invoke)

    def test_bad_request_unsupported_method_put_like(self):
        resource = TestResource()
        environ = {'QUERY_STRING': '', 'REQUEST_METHOD': 'PUT',
                   'wsgi.input': StringIO.StringIO('{}'),
                   'CONTENT_LENGTH': '2',
                   'CONTENT_TYPE': 'application/json'}
        invoke = http_app.HTTPInvocationByMethodWithBody(resource, environ,
                                                         parameters)
        self.assertRaises(http_app.BadRequest, invoke)

    def test_bad_request_unsupported_method_put_like_multi_json(self):
        resource = TestResource()
        body = '{}\r\n{}\r\n'
        environ = {'QUERY_STRING': '', 'REQUEST_METHOD': 'POST',
                   'wsgi.input': StringIO.StringIO(body),
                   'CONTENT_LENGTH': str(len(body)),
                   'CONTENT_TYPE': 'application/x-u1db-multi-json'}
        invoke = http_app.HTTPInvocationByMethodWithBody(resource, environ,
                                                         parameters)
        self.assertRaises(http_app.BadRequest, invoke)


class TestHTTPResponder(tests.TestCase):

    def start_response(self, status, headers):
        self.status = status
        self.headers = dict(headers)
        self.response_body = []

        def write(data):
            self.response_body.append(data)

        return write

    def test_send_response_content_w_headers(self):
        responder = http_app.HTTPResponder(self.start_response)
        responder.send_response_content('foo', headers={'x-a': '1'})
        self.assertEqual('200 OK', self.status)
        self.assertEqual({'content-type': 'application/json',
                          'cache-control': 'no-cache',
                          'x-a': '1', 'content-length': '3'}, self.headers)
        self.assertEqual([], self.response_body)
        self.assertEqual(['foo'], responder.content)

    def test_send_response_json(self):
        responder = http_app.HTTPResponder(self.start_response)
        responder.send_response_json(value='success')
        self.assertEqual('200 OK', self.status)
        expected_body = '{"value": "success"}\r\n'
        self.assertEqual({'content-type': 'application/json',
                          'content-length': str(len(expected_body)),
                          'cache-control': 'no-cache'}, self.headers)
        self.assertEqual([], self.response_body)
        self.assertEqual([expected_body], responder.content)

    def test_send_response_json_status_fail(self):
        responder = http_app.HTTPResponder(self.start_response)
        responder.send_response_json(400)
        self.assertEqual('400 Bad Request', self.status)
        expected_body = '{}\r\n'
        self.assertEqual({'content-type': 'application/json',
                          'content-length': str(len(expected_body)),
                          'cache-control': 'no-cache'}, self.headers)
        self.assertEqual([], self.response_body)
        self.assertEqual([expected_body], responder.content)

    def test_start_finish_response_status_fail(self):
        responder = http_app.HTTPResponder(self.start_response)
        responder.start_response(404, {'error': 'not found'})
        responder.finish_response()
        self.assertEqual('404 Not Found', self.status)
        self.assertEqual({'content-type': 'application/json',
                          'cache-control': 'no-cache'}, self.headers)
        self.assertEqual(['{"error": "not found"}\r\n'], self.response_body)
        self.assertEqual([], responder.content)

    def test_send_stream_entry(self):
        responder = http_app.HTTPResponder(self.start_response)
        responder.content_type = "application/x-u1db-multi-json"
        responder.start_response(200)
        responder.start_stream()
        responder.stream_entry({'entry': 1})
        responder.stream_entry({'entry': 2})
        responder.end_stream()
        responder.finish_response()
        self.assertEqual('200 OK', self.status)
        self.assertEqual({'content-type': 'application/x-u1db-multi-json',
                          'cache-control': 'no-cache'}, self.headers)
        self.assertEqual(['[',
                           '\r\n', '{"entry": 1}',
                           ',\r\n', '{"entry": 2}',
                          '\r\n]\r\n'], self.response_body)
        self.assertEqual([], responder.content)

    def test_send_stream_w_error(self):
        responder = http_app.HTTPResponder(self.start_response)
        responder.content_type = "application/x-u1db-multi-json"
        responder.start_response(200)
        responder.start_stream()
        responder.stream_entry({'entry': 1})
        responder.send_response_json(503, error="unavailable")
        self.assertEqual('200 OK', self.status)
        self.assertEqual({'content-type': 'application/x-u1db-multi-json',
                          'cache-control': 'no-cache'}, self.headers)
        self.assertEqual(['[',
                           '\r\n', '{"entry": 1}'], self.response_body)
        self.assertEqual([',\r\n', '{"error": "unavailable"}\r\n'],
                         responder.content)


class TestHTTPApp(tests.TestCase):

    def setUp(self):
        super(TestHTTPApp, self).setUp()
        self.state = tests.ServerStateForTests()
        self.http_app = http_app.HTTPApp(self.state)
        self.app = paste.fixture.TestApp(self.http_app)
        self.db0 = self.state._create_database('db0')

    def test_bad_request_broken(self):
        resp = self.app.put('/db0/doc/doc1', params='{"x": 1}',
                            headers={'content-type': 'application/foo'},
                            expect_errors=True)
        self.assertEqual(400, resp.status)

    def test_bad_request_dispatch(self):
        resp = self.app.put('/db0/foo/doc1', params='{"x": 1}',
                            headers={'content-type': 'application/json'},
                            expect_errors=True)
        self.assertEqual(400, resp.status)

    def test_version(self):
        resp = self.app.get('/')
        self.assertEqual(200, resp.status)
        self.assertEqual('application/json', resp.header('content-type'))
        self.assertEqual({"version": _u1db_version}, json.loads(resp.body))

    def test_create_database(self):
        resp = self.app.put('/db1', params='{}',
                            headers={'content-type': 'application/json'})
        self.assertEqual(200, resp.status)
        self.assertEqual('application/json', resp.header('content-type'))
        self.assertEqual({'ok': True}, json.loads(resp.body))

        resp = self.app.put('/db1', params='{}',
                            headers={'content-type': 'application/json'})
        self.assertEqual(200, resp.status)
        self.assertEqual('application/json', resp.header('content-type'))
        self.assertEqual({'ok': True}, json.loads(resp.body))

    def test_delete_database(self):
        resp = self.app.delete('/db0')
        self.assertEqual(200, resp.status)
        self.assertRaises(errors.DatabaseDoesNotExist,
                          self.state.check_database, 'db0')

    def test_get_database(self):
        resp = self.app.get('/db0')
        self.assertEqual(200, resp.status)
        self.assertEqual('application/json', resp.header('content-type'))
        self.assertEqual({}, json.loads(resp.body))

    def test_valid_database_names(self):
        resp = self.app.get('/a-database', expect_errors=True)
        self.assertEqual(404, resp.status)

        resp = self.app.get('/db1', expect_errors=True)
        self.assertEqual(404, resp.status)

        resp = self.app.get('/0', expect_errors=True)
        self.assertEqual(404, resp.status)

        resp = self.app.get('/0-0', expect_errors=True)
        self.assertEqual(404, resp.status)

        resp = self.app.get('/org.future', expect_errors=True)
        self.assertEqual(404, resp.status)

    def test_invalid_database_names(self):
        resp = self.app.get('/.a', expect_errors=True)
        self.assertEqual(400, resp.status)

        resp = self.app.get('/-a', expect_errors=True)
        self.assertEqual(400, resp.status)

        resp = self.app.get('/_a', expect_errors=True)
        self.assertEqual(400, resp.status)

    def test_put_doc_create(self):
        resp = self.app.put('/db0/doc/doc1', params='{"x": 1}',
                            headers={'content-type': 'application/json'})
        doc = self.db0.get_doc('doc1')
        self.assertEqual(201, resp.status)  # created
        self.assertEqual('{"x": 1}', doc.get_json())
        self.assertEqual('application/json', resp.header('content-type'))
        self.assertEqual({'rev': doc.rev}, json.loads(resp.body))

    def test_put_doc(self):
        doc = self.db0.create_doc_from_json('{"x": 1}', doc_id='doc1')
        resp = self.app.put('/db0/doc/doc1?old_rev=%s' % doc.rev,
                            params='{"x": 2}',
                            headers={'content-type': 'application/json'})
        doc = self.db0.get_doc('doc1')
        self.assertEqual(200, resp.status)
        self.assertEqual('{"x": 2}', doc.get_json())
        self.assertEqual('application/json', resp.header('content-type'))
        self.assertEqual({'rev': doc.rev}, json.loads(resp.body))

    def test_put_doc_too_large(self):
        self.http_app.max_request_size = 15000
        doc = self.db0.create_doc_from_json('{"x": 1}', doc_id='doc1')
        resp = self.app.put('/db0/doc/doc1?old_rev=%s' % doc.rev,
                            params='{"%s": 2}' % ('z' * 16000),
                            headers={'content-type': 'application/json'},
                            expect_errors=True)
        self.assertEqual(400, resp.status)

    def test_delete_doc(self):
        doc = self.db0.create_doc_from_json('{"x": 1}', doc_id='doc1')
        resp = self.app.delete('/db0/doc/doc1?old_rev=%s' % doc.rev)
        doc = self.db0.get_doc('doc1', include_deleted=True)
        self.assertEqual(None, doc.content)
        self.assertEqual(200, resp.status)
        self.assertEqual('application/json', resp.header('content-type'))
        self.assertEqual({'rev': doc.rev}, json.loads(resp.body))

    def test_get_doc(self):
        doc = self.db0.create_doc_from_json('{"x": 1}', doc_id='doc1')
        resp = self.app.get('/db0/doc/%s' % doc.doc_id)
        self.assertEqual(200, resp.status)
        self.assertEqual('application/json', resp.header('content-type'))
        self.assertEqual('{"x": 1}', resp.body)
        self.assertEqual(doc.rev, resp.header('x-u1db-rev'))
        self.assertEqual('false', resp.header('x-u1db-has-conflicts'))

    def test_get_doc_non_existing(self):
        resp = self.app.get('/db0/doc/not-there', expect_errors=True)
        self.assertEqual(404, resp.status)
        self.assertEqual('application/json', resp.header('content-type'))
        self.assertEqual(
            {"error": "document does not exist"}, json.loads(resp.body))
        self.assertEqual('', resp.header('x-u1db-rev'))
        self.assertEqual('false', resp.header('x-u1db-has-conflicts'))

    def test_get_doc_deleted(self):
        doc = self.db0.create_doc_from_json('{"x": 1}', doc_id='doc1')
        self.db0.delete_doc(doc)
        resp = self.app.get('/db0/doc/doc1', expect_errors=True)
        self.assertEqual(404, resp.status)
        self.assertEqual('application/json', resp.header('content-type'))
        self.assertEqual(
            {"error": errors.DocumentDoesNotExist.wire_description},
            json.loads(resp.body))

    def test_get_doc_deleted_explicit_exclude(self):
        doc = self.db0.create_doc_from_json('{"x": 1}', doc_id='doc1')
        self.db0.delete_doc(doc)
        resp = self.app.get(
            '/db0/doc/doc1?include_deleted=false', expect_errors=True)
        self.assertEqual(404, resp.status)
        self.assertEqual('application/json', resp.header('content-type'))
        self.assertEqual(
            {"error": errors.DocumentDoesNotExist.wire_description},
            json.loads(resp.body))

    def test_get_deleted_doc(self):
        doc = self.db0.create_doc_from_json('{"x": 1}', doc_id='doc1')
        self.db0.delete_doc(doc)
        resp = self.app.get(
            '/db0/doc/doc1?include_deleted=true', expect_errors=True)
        self.assertEqual(404, resp.status)
        self.assertEqual('application/json', resp.header('content-type'))
        self.assertEqual(
            {"error": errors.DOCUMENT_DELETED}, json.loads(resp.body))
        self.assertEqual(doc.rev, resp.header('x-u1db-rev'))
        self.assertEqual('false', resp.header('x-u1db-has-conflicts'))

    def test_get_doc_non_existing_dabase(self):
        resp = self.app.get('/not-there/doc/doc1', expect_errors=True)
        self.assertEqual(404, resp.status)
        self.assertEqual('application/json', resp.header('content-type'))
        self.assertEqual(
            {"error": "database does not exist"}, json.loads(resp.body))

    def test_get_docs(self):
        doc1 = self.db0.create_doc_from_json('{"x": 1}', doc_id='doc1')
        doc2 = self.db0.create_doc_from_json('{"x": 1}', doc_id='doc2')
        ids = ','.join([doc1.doc_id, doc2.doc_id])
        resp = self.app.get('/db0/docs?doc_ids=%s' % ids)
        self.assertEqual(200, resp.status)
        self.assertEqual(
            'application/json', resp.header('content-type'))
        expected = [
            {"content": '{"x": 1}', "doc_rev": "db0:1", "doc_id": "doc1",
             "has_conflicts": False},
            {"content": '{"x": 1}', "doc_rev": "db0:1", "doc_id": "doc2",
             "has_conflicts": False}]
        self.assertEqual(expected, json.loads(resp.body))

    def test_get_docs_missing_doc_ids(self):
        resp = self.app.get('/db0/docs', expect_errors=True)
        self.assertEqual(400, resp.status)
        self.assertEqual('application/json', resp.header('content-type'))
        self.assertEqual(
            {"error": "missing document ids"}, json.loads(resp.body))

    def test_get_docs_empty_doc_ids(self):
        resp = self.app.get('/db0/docs?doc_ids=', expect_errors=True)
        self.assertEqual(400, resp.status)
        self.assertEqual('application/json', resp.header('content-type'))
        self.assertEqual(
            {"error": "missing document ids"}, json.loads(resp.body))

    def test_get_docs_percent(self):
        doc1 = self.db0.create_doc_from_json('{"x": 1}', doc_id='doc%1')
        doc2 = self.db0.create_doc_from_json('{"x": 1}', doc_id='doc2')
        ids = ','.join([doc1.doc_id, doc2.doc_id])
        resp = self.app.get('/db0/docs?doc_ids=%s' % ids)
        self.assertEqual(200, resp.status)
        self.assertEqual(
            'application/json', resp.header('content-type'))
        expected = [
            {"content": '{"x": 1}', "doc_rev": "db0:1", "doc_id": "doc%1",
             "has_conflicts": False},
            {"content": '{"x": 1}', "doc_rev": "db0:1", "doc_id": "doc2",
             "has_conflicts": False}]
        self.assertEqual(expected, json.loads(resp.body))

    def test_get_docs_deleted(self):
        doc1 = self.db0.create_doc_from_json('{"x": 1}', doc_id='doc1')
        doc2 = self.db0.create_doc_from_json('{"x": 1}', doc_id='doc2')
        self.db0.delete_doc(doc2)
        ids = ','.join([doc1.doc_id, doc2.doc_id])
        resp = self.app.get('/db0/docs?doc_ids=%s' % ids)
        self.assertEqual(200, resp.status)
        self.assertEqual(
            'application/json', resp.header('content-type'))
        expected = [
            {"content": '{"x": 1}', "doc_rev": "db0:1", "doc_id": "doc1",
             "has_conflicts": False}]
        self.assertEqual(expected, json.loads(resp.body))

    def test_get_docs_include_deleted(self):
        doc1 = self.db0.create_doc_from_json('{"x": 1}', doc_id='doc1')
        doc2 = self.db0.create_doc_from_json('{"x": 1}', doc_id='doc2')
        self.db0.delete_doc(doc2)
        ids = ','.join([doc1.doc_id, doc2.doc_id])
        resp = self.app.get('/db0/docs?doc_ids=%s&include_deleted=true' % ids)
        self.assertEqual(200, resp.status)
        self.assertEqual(
            'application/json', resp.header('content-type'))
        expected = [
            {"content": '{"x": 1}', "doc_rev": "db0:1", "doc_id": "doc1",
             "has_conflicts": False},
            {"content": None, "doc_rev": "db0:2", "doc_id": "doc2",
             "has_conflicts": False}]
        self.assertEqual(expected, json.loads(resp.body))

    def test_get_sync_info(self):
        self.db0._set_replica_gen_and_trans_id('other-id', 1, 'T-transid')
        resp = self.app.get('/db0/sync-from/other-id')
        self.assertEqual(200, resp.status)
        self.assertEqual('application/json', resp.header('content-type'))
        self.assertEqual(dict(target_replica_uid='db0',
                              target_replica_generation=0,
                              target_replica_transaction_id='',
                              source_replica_uid='other-id',
                              source_replica_generation=1,
                              source_transaction_id='T-transid'),
                              json.loads(resp.body))

    def test_record_sync_info(self):
        resp = self.app.put('/db0/sync-from/other-id',
            params='{"generation": 2, "transaction_id": "T-transid"}',
            headers={'content-type': 'application/json'})
        self.assertEqual(200, resp.status)
        self.assertEqual('application/json', resp.header('content-type'))
        self.assertEqual({'ok': True}, json.loads(resp.body))
        self.assertEqual(
            (2, 'T-transid'),
            self.db0._get_replica_gen_and_trans_id('other-id'))

    def test_sync_exchange_send(self):
        entries = {
            10: {'id': 'doc-here', 'rev': 'replica:1', 'content':
                 '{"value": "here"}', 'gen': 10, 'trans_id': 'T-sid'},
            11: {'id': 'doc-here2', 'rev': 'replica:1', 'content':
                 '{"value": "here2"}', 'gen': 11, 'trans_id': 'T-sed'}
            }

        gens = []
        _do_set_replica_gen_and_trans_id = \
            self.db0._do_set_replica_gen_and_trans_id

        def set_sync_generation_witness(other_uid, other_gen, other_trans_id):
            gens.append((other_uid, other_gen))
            _do_set_replica_gen_and_trans_id(
                other_uid, other_gen, other_trans_id)
            self.assertGetDoc(self.db0, entries[other_gen]['id'],
                              entries[other_gen]['rev'],
                              entries[other_gen]['content'], False)

        self.patch(
            self.db0, '_do_set_replica_gen_and_trans_id',
            set_sync_generation_witness)

        args = dict(last_known_generation=0)
        body = ("[\r\n" +
                "%s,\r\n" % json.dumps(args) +
                "%s,\r\n" % json.dumps(entries[10]) +
                "%s\r\n" % json.dumps(entries[11]) +
                "]\r\n")
        resp = self.app.post('/db0/sync-from/replica',
                            params=body,
                            headers={'content-type':
                                     'application/x-u1db-sync-stream'})
        self.assertEqual(200, resp.status)
        self.assertEqual('application/x-u1db-sync-stream',
                         resp.header('content-type'))
        bits = resp.body.split('\r\n')
        self.assertEqual('[', bits[0])
        last_trans_id = self.db0._get_transaction_log()[-1][1]
        self.assertEqual({'new_generation': 2,
                          'new_transaction_id': last_trans_id},
                         json.loads(bits[1]))
        self.assertEqual(']', bits[2])
        self.assertEqual('', bits[3])
        self.assertEqual([('replica', 10), ('replica', 11)], gens)

    def test_sync_exchange_send_ensure(self):
        entries = {
            10: {'id': 'doc-here', 'rev': 'replica:1', 'content':
                 '{"value": "here"}', 'gen': 10, 'trans_id': 'T-sid'},
            11: {'id': 'doc-here2', 'rev': 'replica:1', 'content':
                 '{"value": "here2"}', 'gen': 11, 'trans_id': 'T-sed'}
            }

        args = dict(last_known_generation=0, ensure=True)
        body = ("[\r\n" +
                "%s,\r\n" % json.dumps(args) +
                "%s,\r\n" % json.dumps(entries[10]) +
                "%s\r\n" % json.dumps(entries[11]) +
                "]\r\n")
        resp = self.app.post('/dbnew/sync-from/replica',
                            params=body,
                            headers={'content-type':
                                     'application/x-u1db-sync-stream'})
        self.assertEqual(200, resp.status)
        self.assertEqual('application/x-u1db-sync-stream',
                         resp.header('content-type'))
        bits = resp.body.split('\r\n')
        self.assertEqual('[', bits[0])
        dbnew = self.state.open_database("dbnew")
        last_trans_id = dbnew._get_transaction_log()[-1][1]
        self.assertEqual({'new_generation': 2,
                          'new_transaction_id': last_trans_id,
                          'replica_uid': dbnew._replica_uid},
                         json.loads(bits[1]))
        self.assertEqual(']', bits[2])
        self.assertEqual('', bits[3])

    def test_sync_exchange_send_entry_too_large(self):
        self.patch(http_app.SyncResource, 'max_request_size', 20000)
        self.patch(http_app.SyncResource, 'max_entry_size', 10000)
        entries = {
            10: {'id': 'doc-here', 'rev': 'replica:1', 'content':
                 '{"value": "%s"}' % ('H' * 11000), 'gen': 10},
            }
        args = dict(last_known_generation=0)
        body = ("[\r\n" +
                "%s,\r\n" % json.dumps(args) +
                "%s\r\n" % json.dumps(entries[10]) +
                "]\r\n")
        resp = self.app.post('/db0/sync-from/replica',
                            params=body,
                            headers={'content-type':
                                     'application/x-u1db-sync-stream'},
                             expect_errors=True)
        self.assertEqual(400, resp.status)

    def test_sync_exchange_receive(self):
        doc = self.db0.create_doc_from_json('{"value": "there"}')
        doc2 = self.db0.create_doc_from_json('{"value": "there2"}')
        args = dict(last_known_generation=0)
        body = "[\r\n%s\r\n]" % json.dumps(args)
        resp = self.app.post('/db0/sync-from/replica',
                            params=body,
                            headers={'content-type':
                                     'application/x-u1db-sync-stream'})
        self.assertEqual(200, resp.status)
        self.assertEqual('application/x-u1db-sync-stream',
                         resp.header('content-type'))
        parts = resp.body.splitlines()
        self.assertEqual(5, len(parts))
        self.assertEqual('[', parts[0])
        last_trans_id = self.db0._get_transaction_log()[-1][1]
        self.assertEqual({'new_generation': 2,
                          'new_transaction_id': last_trans_id},
                         json.loads(parts[1].rstrip(",")))
        part2 = json.loads(parts[2].rstrip(","))
        self.assertTrue(part2['trans_id'].startswith('T-'))
        self.assertEqual('{"value": "there"}', part2['content'])
        self.assertEqual(doc.rev, part2['rev'])
        self.assertEqual(doc.doc_id, part2['id'])
        self.assertEqual(1, part2['gen'])
        part3 = json.loads(parts[3].rstrip(","))
        self.assertTrue(part3['trans_id'].startswith('T-'))
        self.assertEqual('{"value": "there2"}', part3['content'])
        self.assertEqual(doc2.rev, part3['rev'])
        self.assertEqual(doc2.doc_id, part3['id'])
        self.assertEqual(2, part3['gen'])
        self.assertEqual(']', parts[4])

    def test_sync_exchange_error_in_stream(self):
        args = dict(last_known_generation=0)
        body = "[\r\n%s\r\n]" % json.dumps(args)

        def boom(self, return_doc_cb):
            raise errors.Unavailable

        self.patch(sync.SyncExchange, 'return_docs',
                   boom)
        resp = self.app.post('/db0/sync-from/replica',
                            params=body,
                            headers={'content-type':
                                     'application/x-u1db-sync-stream'})
        self.assertEqual(200, resp.status)
        self.assertEqual('application/x-u1db-sync-stream',
                         resp.header('content-type'))
        parts = resp.body.splitlines()
        self.assertEqual(3, len(parts))
        self.assertEqual('[', parts[0])
        self.assertEqual({'new_generation': 0, 'new_transaction_id': ''},
                         json.loads(parts[1].rstrip(",")))
        self.assertEqual({'error': 'unavailable'}, json.loads(parts[2]))


class TestRequestHooks(tests.TestCase):

    def setUp(self):
        super(TestRequestHooks, self).setUp()
        self.state = tests.ServerStateForTests()
        self.http_app = http_app.HTTPApp(self.state)
        self.app = paste.fixture.TestApp(self.http_app)
        self.db0 = self.state._create_database('db0')

    def test_begin_and_done(self):
        calls = []

        def begin(environ):
            self.assertTrue('PATH_INFO' in environ)
            calls.append('begin')

        def done(environ):
            self.assertTrue('PATH_INFO' in environ)
            calls.append('done')

        self.http_app.request_begin = begin
        self.http_app.request_done = done

        doc = self.db0.create_doc_from_json('{"x": 1}', doc_id='doc1')
        self.app.get('/db0/doc/%s' % doc.doc_id)

        self.assertEqual(['begin', 'done'], calls)

    def test_bad_request(self):
        calls = []

        def begin(environ):
            self.assertTrue('PATH_INFO' in environ)
            calls.append('begin')

        def bad_request(environ):
            self.assertTrue('PATH_INFO' in environ)
            calls.append('bad-request')

        self.http_app.request_begin = begin
        self.http_app.request_bad_request = bad_request
        # shouldn't be called
        self.http_app.request_done = lambda env: 1 / 0

        resp = self.app.put('/db0/foo/doc1', params='{"x": 1}',
                            headers={'content-type': 'application/json'},
                            expect_errors=True)
        self.assertEqual(400, resp.status)
        self.assertEqual(['begin', 'bad-request'], calls)


class TestHTTPErrors(tests.TestCase):

    def test_wire_description_to_status(self):
        self.assertNotIn("error", http_errors.wire_description_to_status)


class TestHTTPAppErrorHandling(tests.TestCase):

    def setUp(self):
        super(TestHTTPAppErrorHandling, self).setUp()
        self.exc = None
        self.state = tests.ServerStateForTests()

        class ErroringResource(object):

            def post(_, args, content):
                raise self.exc

        def lookup_resource(environ, responder):
            return ErroringResource()

        self.http_app = http_app.HTTPApp(self.state)
        self.http_app._lookup_resource = lookup_resource
        self.app = paste.fixture.TestApp(self.http_app)

    def test_RevisionConflict_etc(self):
        self.exc = errors.RevisionConflict()
        resp = self.app.post('/req', params='{}',
                             headers={'content-type': 'application/json'},
                             expect_errors=True)
        self.assertEqual(409, resp.status)
        self.assertEqual('application/json', resp.header('content-type'))
        self.assertEqual({"error": "revision conflict"},
                         json.loads(resp.body))

    def test_Unavailable(self):
        self.exc = errors.Unavailable
        resp = self.app.post('/req', params='{}',
                             headers={'content-type': 'application/json'},
                             expect_errors=True)
        self.assertEqual(503, resp.status)
        self.assertEqual('application/json', resp.header('content-type'))
        self.assertEqual({"error": "unavailable"},
                         json.loads(resp.body))

    def test_generic_u1db_errors(self):
        self.exc = errors.U1DBError()
        resp = self.app.post('/req', params='{}',
                             headers={'content-type': 'application/json'},
                             expect_errors=True)
        self.assertEqual(500, resp.status)
        self.assertEqual('application/json', resp.header('content-type'))
        self.assertEqual({"error": "error"},
                         json.loads(resp.body))

    def test_generic_u1db_errors_hooks(self):
        calls = []

        def begin(environ):
            self.assertTrue('PATH_INFO' in environ)
            calls.append('begin')

        def u1db_error(environ, exc):
            self.assertTrue('PATH_INFO' in environ)
            calls.append(('error', exc))

        self.http_app.request_begin = begin
        self.http_app.request_u1db_error = u1db_error
        # shouldn't be called
        self.http_app.request_done = lambda env: 1 / 0

        self.exc = errors.U1DBError()
        resp = self.app.post('/req', params='{}',
                             headers={'content-type': 'application/json'},
                             expect_errors=True)
        self.assertEqual(500, resp.status)
        self.assertEqual(['begin', ('error', self.exc)], calls)

    def test_failure(self):
        class Failure(Exception):
            pass
        self.exc = Failure()
        self.assertRaises(Failure, self.app.post, '/req', params='{}',
                          headers={'content-type': 'application/json'})

    def test_failure_hooks(self):
        class Failure(Exception):
            pass
        calls = []

        def begin(environ):
            calls.append('begin')

        def failed(environ):
            self.assertTrue('PATH_INFO' in environ)
            calls.append(('failed', sys.exc_info()))

        self.http_app.request_begin = begin
        self.http_app.request_failed = failed
        # shouldn't be called
        self.http_app.request_done = lambda env: 1 / 0

        self.exc = Failure()
        self.assertRaises(Failure, self.app.post, '/req', params='{}',
                          headers={'content-type': 'application/json'})

        self.assertEqual(2, len(calls))
        self.assertEqual('begin', calls[0])
        marker, (exc_type, exc, tb) = calls[1]
        self.assertEqual('failed', marker)
        self.assertEqual(self.exc, exc)


class TestPluggableSyncExchange(tests.TestCase):

    def setUp(self):
        super(TestPluggableSyncExchange, self).setUp()
        self.state = tests.ServerStateForTests()
        self.state.ensure_database('foo')

    def test_plugging(self):

        class MySyncExchange(object):
            def __init__(self, db, source_replica_uid, last_known_generation):
                pass

        class MySyncResource(http_app.SyncResource):
            sync_exchange_class = MySyncExchange

        sync_res = MySyncResource('foo', 'src', self.state, None)
        sync_res.post_args(
            {'last_known_generation': 0, 'last_known_trans_id': None}, '{}')
        self.assertIsInstance(sync_res.sync_exch, MySyncExchange)
