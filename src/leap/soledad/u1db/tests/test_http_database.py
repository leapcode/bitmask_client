# Copyright 2011 Canonical Ltd.
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

import inspect
try:
    import simplejson as json
except ImportError:
    import json  # noqa

from u1db import (
    errors,
    Document,
    tests,
    )
from u1db.remote import (
    http_database,
    http_target,
    )
from u1db.tests.test_remote_sync_target import (
    make_http_app,
)


class TestHTTPDatabaseSimpleOperations(tests.TestCase):

    def setUp(self):
        super(TestHTTPDatabaseSimpleOperations, self).setUp()
        self.db = http_database.HTTPDatabase('dbase')
        self.db._conn = object()  # crash if used
        self.got = None
        self.response_val = None

        def _request(method, url_parts, params=None, body=None,
                                                     content_type=None):
            self.got = method, url_parts, params, body, content_type
            if isinstance(self.response_val, Exception):
                raise self.response_val
            return self.response_val

        def _request_json(method, url_parts, params=None, body=None,
                                                          content_type=None):
            self.got = method, url_parts, params, body, content_type
            if isinstance(self.response_val, Exception):
                raise self.response_val
            return self.response_val

        self.db._request = _request
        self.db._request_json = _request_json

    def test__sanity_same_signature(self):
        my_request_sig = inspect.getargspec(self.db._request)
        my_request_sig = (['self'] + my_request_sig[0],) + my_request_sig[1:]
        self.assertEqual(my_request_sig,
                       inspect.getargspec(http_database.HTTPDatabase._request))
        my_request_json_sig = inspect.getargspec(self.db._request_json)
        my_request_json_sig = ((['self'] + my_request_json_sig[0],) +
                               my_request_json_sig[1:])
        self.assertEqual(my_request_json_sig,
                  inspect.getargspec(http_database.HTTPDatabase._request_json))

    def test__ensure(self):
        self.response_val = {'ok': True}, {}
        self.db._ensure()
        self.assertEqual(('PUT', [], {}, {}, None), self.got)

    def test__delete(self):
        self.response_val = {'ok': True}, {}
        self.db._delete()
        self.assertEqual(('DELETE', [], {}, {}, None), self.got)

    def test__check(self):
        self.response_val = {}, {}
        res = self.db._check()
        self.assertEqual({}, res)
        self.assertEqual(('GET', [], None, None, None), self.got)

    def test_put_doc(self):
        self.response_val = {'rev': 'doc-rev'}, {}
        doc = Document('doc-id', None, '{"v": 1}')
        res = self.db.put_doc(doc)
        self.assertEqual('doc-rev', res)
        self.assertEqual('doc-rev', doc.rev)
        self.assertEqual(('PUT', ['doc', 'doc-id'], {},
                          '{"v": 1}', 'application/json'), self.got)

        self.response_val = {'rev': 'doc-rev-2'}, {}
        doc.content = {"v": 2}
        res = self.db.put_doc(doc)
        self.assertEqual('doc-rev-2', res)
        self.assertEqual('doc-rev-2', doc.rev)
        self.assertEqual(('PUT', ['doc', 'doc-id'], {'old_rev': 'doc-rev'},
                          '{"v": 2}', 'application/json'), self.got)

    def test_get_doc(self):
        self.response_val = '{"v": 2}', {'x-u1db-rev': 'doc-rev',
                                         'x-u1db-has-conflicts': 'false'}
        self.assertGetDoc(self.db, 'doc-id', 'doc-rev', '{"v": 2}', False)
        self.assertEqual(
            ('GET', ['doc', 'doc-id'], {'include_deleted': False}, None, None),
            self.got)

    def test_get_doc_non_existing(self):
        self.response_val = errors.DocumentDoesNotExist()
        self.assertIs(None, self.db.get_doc('not-there'))
        self.assertEqual(
            ('GET', ['doc', 'not-there'], {'include_deleted': False}, None,
             None), self.got)

    def test_get_doc_deleted(self):
        self.response_val = errors.DocumentDoesNotExist()
        self.assertIs(None, self.db.get_doc('deleted'))
        self.assertEqual(
            ('GET', ['doc', 'deleted'], {'include_deleted': False}, None,
             None), self.got)

    def test_get_doc_deleted_include_deleted(self):
        self.response_val = errors.HTTPError(404,
                                             json.dumps(
                                             {"error": errors.DOCUMENT_DELETED}
                                             ),
                                             {'x-u1db-rev': 'doc-rev-gone',
                                              'x-u1db-has-conflicts': 'false'})
        doc = self.db.get_doc('deleted', include_deleted=True)
        self.assertEqual('deleted', doc.doc_id)
        self.assertEqual('doc-rev-gone', doc.rev)
        self.assertIs(None, doc.content)
        self.assertEqual(
            ('GET', ['doc', 'deleted'], {'include_deleted': True}, None, None),
            self.got)

    def test_get_doc_pass_through_errors(self):
        self.response_val = errors.HTTPError(500, 'Crash.')
        self.assertRaises(errors.HTTPError,
                          self.db.get_doc, 'something-something')

    def test_create_doc_with_id(self):
        self.response_val = {'rev': 'doc-rev'}, {}
        new_doc = self.db.create_doc_from_json('{"v": 1}', doc_id='doc-id')
        self.assertEqual('doc-rev', new_doc.rev)
        self.assertEqual('doc-id', new_doc.doc_id)
        self.assertEqual('{"v": 1}', new_doc.get_json())
        self.assertEqual(('PUT', ['doc', 'doc-id'], {},
                          '{"v": 1}', 'application/json'), self.got)

    def test_create_doc_without_id(self):
        self.response_val = {'rev': 'doc-rev-2'}, {}
        new_doc = self.db.create_doc_from_json('{"v": 3}')
        self.assertEqual('D-', new_doc.doc_id[:2])
        self.assertEqual('doc-rev-2', new_doc.rev)
        self.assertEqual('{"v": 3}', new_doc.get_json())
        self.assertEqual(('PUT', ['doc', new_doc.doc_id], {},
                          '{"v": 3}', 'application/json'), self.got)

    def test_delete_doc(self):
        self.response_val = {'rev': 'doc-rev-gone'}, {}
        doc = Document('doc-id', 'doc-rev', None)
        self.db.delete_doc(doc)
        self.assertEqual('doc-rev-gone', doc.rev)
        self.assertEqual(('DELETE', ['doc', 'doc-id'], {'old_rev': 'doc-rev'},
                          None, None), self.got)

    def test_get_sync_target(self):
        st = self.db.get_sync_target()
        self.assertIsInstance(st, http_target.HTTPSyncTarget)
        self.assertEqual(st._url, self.db._url)

    def test_get_sync_target_inherits_oauth_credentials(self):
        self.db.set_oauth_credentials(tests.consumer1.key,
                                      tests.consumer1.secret,
                                      tests.token1.key, tests.token1.secret)
        st = self.db.get_sync_target()
        self.assertEqual(self.db._creds, st._creds)


class TestHTTPDatabaseCtrWithCreds(tests.TestCase):

    def test_ctr_with_creds(self):
        db1 = http_database.HTTPDatabase('http://dbs/db', creds={'oauth': {
            'consumer_key': tests.consumer1.key,
            'consumer_secret': tests.consumer1.secret,
            'token_key': tests.token1.key,
            'token_secret': tests.token1.secret
            }})
        self.assertIn('oauth',  db1._creds)


class TestHTTPDatabaseIntegration(tests.TestCaseWithServer):

    make_app_with_state = staticmethod(make_http_app)

    def setUp(self):
        super(TestHTTPDatabaseIntegration, self).setUp()
        self.startServer()

    def test_non_existing_db(self):
        db = http_database.HTTPDatabase(self.getURL('not-there'))
        self.assertRaises(errors.DatabaseDoesNotExist, db.get_doc, 'doc1')

    def test__ensure(self):
        db = http_database.HTTPDatabase(self.getURL('new'))
        db._ensure()
        self.assertIs(None, db.get_doc('doc1'))

    def test__delete(self):
        self.request_state._create_database('db0')
        db = http_database.HTTPDatabase(self.getURL('db0'))
        db._delete()
        self.assertRaises(errors.DatabaseDoesNotExist,
                          self.request_state.check_database, 'db0')

    def test_open_database_existing(self):
        self.request_state._create_database('db0')
        db = http_database.HTTPDatabase.open_database(self.getURL('db0'),
                                                      create=False)
        self.assertIs(None, db.get_doc('doc1'))

    def test_open_database_non_existing(self):
        self.assertRaises(errors.DatabaseDoesNotExist,
                          http_database.HTTPDatabase.open_database,
                          self.getURL('not-there'),
                          create=False)

    def test_open_database_create(self):
        db = http_database.HTTPDatabase.open_database(self.getURL('new'),
                                                      create=True)
        self.assertIs(None, db.get_doc('doc1'))

    def test_delete_database_existing(self):
        self.request_state._create_database('db0')
        http_database.HTTPDatabase.delete_database(self.getURL('db0'))
        self.assertRaises(errors.DatabaseDoesNotExist,
                          self.request_state.check_database, 'db0')

    def test_doc_ids_needing_quoting(self):
        db0 = self.request_state._create_database('db0')
        db = http_database.HTTPDatabase.open_database(self.getURL('db0'),
                                                      create=False)
        doc = Document('%fff', None, '{}')
        db.put_doc(doc)
        self.assertGetDoc(db0, '%fff', doc.rev, '{}', False)
        self.assertGetDoc(db, '%fff', doc.rev, '{}', False)
