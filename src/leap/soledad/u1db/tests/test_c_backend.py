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

try:
    import simplejson as json
except ImportError:
    import json  # noqa
from u1db import (
    Document,
    errors,
    tests,
    )
from u1db.tests import c_backend_wrapper, c_backend_error
from u1db.tests.test_remote_sync_target import (
    make_http_app,
    make_oauth_http_app
    )


class TestCDatabaseExists(tests.TestCase):

    def test_c_backend_compiled(self):
        if c_backend_wrapper is None:
            self.fail("Could not import the c_backend_wrapper module."
                      " Was it compiled properly?\n%s" % (c_backend_error,))


# Rather than lots of failing tests, we have the above check to test that the
# module exists, and all these tests just get skipped
class BackendTests(tests.TestCase):

    def setUp(self):
        super(BackendTests, self).setUp()
        if c_backend_wrapper is None:
            self.skipTest("The c_backend_wrapper could not be imported")


class TestCDatabase(BackendTests):

    def test_exists(self):
        if c_backend_wrapper is None:
            self.fail("Could not import the c_backend_wrapper module."
                      " Was it compiled properly?")
        db = c_backend_wrapper.CDatabase(':memory:')
        self.assertEqual(':memory:', db._filename)

    def test__is_closed(self):
        db = c_backend_wrapper.CDatabase(':memory:')
        self.assertTrue(db._sql_is_open())
        db.close()
        self.assertFalse(db._sql_is_open())

    def test__run_sql(self):
        db = c_backend_wrapper.CDatabase(':memory:')
        self.assertTrue(db._sql_is_open())
        self.assertEqual([], db._run_sql('CREATE TABLE test (id INTEGER)'))
        self.assertEqual([], db._run_sql('INSERT INTO test VALUES (1)'))
        self.assertEqual([('1',)], db._run_sql('SELECT * FROM test'))

    def test__get_generation(self):
        db = c_backend_wrapper.CDatabase(':memory:')
        self.assertEqual(0, db._get_generation())
        db.create_doc_from_json(tests.simple_doc)
        self.assertEqual(1, db._get_generation())

    def test__get_generation_info(self):
        db = c_backend_wrapper.CDatabase(':memory:')
        self.assertEqual((0, ''), db._get_generation_info())
        db.create_doc_from_json(tests.simple_doc)
        info = db._get_generation_info()
        self.assertEqual(1, info[0])
        self.assertTrue(info[1].startswith('T-'))

    def test__set_replica_uid(self):
        db = c_backend_wrapper.CDatabase(':memory:')
        self.assertIsNot(None, db._replica_uid)
        db._set_replica_uid('foo')
        self.assertEqual([('foo',)], db._run_sql(
            "SELECT value FROM u1db_config WHERE name='replica_uid'"))

    def test_default_replica_uid(self):
        self.db = c_backend_wrapper.CDatabase(':memory:')
        self.assertIsNot(None, self.db._replica_uid)
        self.assertEqual(32, len(self.db._replica_uid))
        # casting to an int from the uid *is* the check for correct behavior.
        int(self.db._replica_uid, 16)

    def test_get_conflicts_with_borked_data(self):
        self.db = c_backend_wrapper.CDatabase(':memory:')
        # We add an entry to conflicts, but not to documents, which is an
        # invalid situation
        self.db._run_sql("INSERT INTO conflicts"
                         " VALUES ('doc-id', 'doc-rev', '{}')")
        self.assertRaises(Exception, self.db.get_doc_conflicts, 'doc-id')

    def test_create_index_list(self):
        # We manually poke data into the DB, so that we test just the "get_doc"
        # code, rather than also testing the index management code.
        self.db = c_backend_wrapper.CDatabase(':memory:')
        doc = self.db.create_doc_from_json(tests.simple_doc)
        self.db.create_index_list("key-idx", ["key"])
        docs = self.db.get_from_index('key-idx', 'value')
        self.assertEqual([doc], docs)

    def test_create_index_list_on_non_ascii_field_name(self):
        self.db = c_backend_wrapper.CDatabase(':memory:')
        doc = self.db.create_doc_from_json(json.dumps({u'\xe5': 'value'}))
        self.db.create_index_list('test-idx', [u'\xe5'])
        self.assertEqual([doc], self.db.get_from_index('test-idx', 'value'))

    def test_list_indexes_with_non_ascii_field_names(self):
        self.db = c_backend_wrapper.CDatabase(':memory:')
        self.db.create_index_list('test-idx', [u'\xe5'])
        self.assertEqual(
            [('test-idx', [u'\xe5'])], self.db.list_indexes())

    def test_create_index_evaluates_it(self):
        self.db = c_backend_wrapper.CDatabase(':memory:')
        doc = self.db.create_doc_from_json(tests.simple_doc)
        self.db.create_index_list('test-idx', ['key'])
        self.assertEqual([doc], self.db.get_from_index('test-idx', 'value'))

    def test_wildcard_matches_unicode_value(self):
        self.db = c_backend_wrapper.CDatabase(':memory:')
        doc = self.db.create_doc_from_json(json.dumps({"key": u"valu\xe5"}))
        self.db.create_index_list('test-idx', ['key'])
        self.assertEqual([doc], self.db.get_from_index('test-idx', '*'))

    def test_create_index_fails_if_name_taken(self):
        self.db = c_backend_wrapper.CDatabase(':memory:')
        self.db.create_index_list('test-idx', ['key'])
        self.assertRaises(errors.IndexNameTakenError,
                          self.db.create_index_list,
                          'test-idx', ['stuff'])

    def test_create_index_does_not_fail_if_name_taken_with_same_index(self):
        self.db = c_backend_wrapper.CDatabase(':memory:')
        self.db.create_index_list('test-idx', ['key'])
        self.db.create_index_list('test-idx', ['key'])
        self.assertEqual([('test-idx', ['key'])], self.db.list_indexes())

    def test_create_index_after_deleting_document(self):
        self.db = c_backend_wrapper.CDatabase(':memory:')
        doc = self.db.create_doc_from_json(tests.simple_doc)
        doc2 = self.db.create_doc_from_json(tests.simple_doc)
        self.db.delete_doc(doc2)
        self.db.create_index_list('test-idx', ['key'])
        self.assertEqual([doc], self.db.get_from_index('test-idx', 'value'))

    def test_get_from_index(self):
        # We manually poke data into the DB, so that we test just the "get_doc"
        # code, rather than also testing the index management code.
        self.db = c_backend_wrapper.CDatabase(':memory:')
        doc = self.db.create_doc_from_json(tests.simple_doc)
        self.db.create_index("key-idx", "key")
        docs = self.db.get_from_index('key-idx', 'value')
        self.assertEqual([doc], docs)

    def test_get_from_index_list(self):
        # We manually poke data into the DB, so that we test just the "get_doc"
        # code, rather than also testing the index management code.
        self.db = c_backend_wrapper.CDatabase(':memory:')
        doc = self.db.create_doc_from_json(tests.simple_doc)
        self.db.create_index("key-idx", "key")
        docs = self.db.get_from_index_list('key-idx', ['value'])
        self.assertEqual([doc], docs)

    def test_get_from_index_list_multi(self):
        self.db = c_backend_wrapper.CDatabase(':memory:')
        content = '{"key": "value", "key2": "value2"}'
        doc = self.db.create_doc_from_json(content)
        self.db.create_index('test-idx', 'key', 'key2')
        self.assertEqual(
            [doc],
            self.db.get_from_index_list('test-idx', ['value', 'value2']))

    def test_get_from_index_list_multi_ordered(self):
        self.db = c_backend_wrapper.CDatabase(':memory:')
        doc1 = self.db.create_doc_from_json(
            '{"key": "value3", "key2": "value4"}')
        doc2 = self.db.create_doc_from_json(
            '{"key": "value2", "key2": "value3"}')
        doc3 = self.db.create_doc_from_json(
            '{"key": "value2", "key2": "value2"}')
        doc4 = self.db.create_doc_from_json(
            '{"key": "value1", "key2": "value1"}')
        self.db.create_index('test-idx', 'key', 'key2')
        self.assertEqual(
            [doc4, doc3, doc2, doc1],
            self.db.get_from_index_list('test-idx', ['v*', '*']))

    def test_get_from_index_2(self):
        self.db = c_backend_wrapper.CDatabase(':memory:')
        doc = self.db.create_doc_from_json(tests.nested_doc)
        self.db.create_index("multi-idx", "key", "sub.doc")
        docs = self.db.get_from_index('multi-idx', 'value', 'underneath')
        self.assertEqual([doc], docs)

    def test_get_index_keys(self):
        self.db = c_backend_wrapper.CDatabase(':memory:')
        self.db.create_doc_from_json(tests.simple_doc)
        self.db.create_index("key-idx", "key")
        keys = self.db.get_index_keys('key-idx')
        self.assertEqual([("value",)], keys)

    def test__query_init_one_field(self):
        self.db = c_backend_wrapper.CDatabase(':memory:')
        self.db.create_index("key-idx", "key")
        query = self.db._query_init("key-idx")
        self.assertEqual("key-idx", query.index_name)
        self.assertEqual(1, query.num_fields)
        self.assertEqual(["key"], query.fields)

    def test__query_init_two_fields(self):
        self.db = c_backend_wrapper.CDatabase(':memory:')
        self.db.create_index("two-idx", "key", "key2")
        query = self.db._query_init("two-idx")
        self.assertEqual("two-idx", query.index_name)
        self.assertEqual(2, query.num_fields)
        self.assertEqual(["key", "key2"], query.fields)

    def assertFormatQueryEquals(self, expected, wildcards, fields):
        val, w = c_backend_wrapper._format_query(fields)
        self.assertEqual(expected, val)
        self.assertEqual(wildcards, w)

    def test__format_query(self):
        self.assertFormatQueryEquals(
            "SELECT d0.doc_id FROM document_fields d0"
            " WHERE d0.field_name = ? AND d0.value = ? ORDER BY d0.value",
            [0], ["1"])
        self.assertFormatQueryEquals(
            "SELECT d0.doc_id"
            " FROM document_fields d0, document_fields d1"
            " WHERE d0.field_name = ? AND d0.value = ?"
            " AND d0.doc_id = d1.doc_id"
            " AND d1.field_name = ? AND d1.value = ?"
            " ORDER BY d0.value, d1.value",
            [0, 0], ["1", "2"])
        self.assertFormatQueryEquals(
            "SELECT d0.doc_id"
            " FROM document_fields d0, document_fields d1, document_fields d2"
            " WHERE d0.field_name = ? AND d0.value = ?"
            " AND d0.doc_id = d1.doc_id"
            " AND d1.field_name = ? AND d1.value = ?"
            " AND d0.doc_id = d2.doc_id"
            " AND d2.field_name = ? AND d2.value = ?"
            " ORDER BY d0.value, d1.value, d2.value",
            [0, 0, 0], ["1", "2", "3"])

    def test__format_query_wildcard(self):
        self.assertFormatQueryEquals(
            "SELECT d0.doc_id FROM document_fields d0"
            " WHERE d0.field_name = ? AND d0.value NOT NULL ORDER BY d0.value",
            [1], ["*"])
        self.assertFormatQueryEquals(
            "SELECT d0.doc_id"
            " FROM document_fields d0, document_fields d1"
            " WHERE d0.field_name = ? AND d0.value = ?"
            " AND d0.doc_id = d1.doc_id"
            " AND d1.field_name = ? AND d1.value NOT NULL"
            " ORDER BY d0.value, d1.value",
            [0, 1], ["1", "*"])

    def test__format_query_glob(self):
        self.assertFormatQueryEquals(
            "SELECT d0.doc_id FROM document_fields d0"
            " WHERE d0.field_name = ? AND d0.value GLOB ? ORDER BY d0.value",
            [2], ["1*"])


class TestCSyncTarget(BackendTests):

    def setUp(self):
        super(TestCSyncTarget, self).setUp()
        self.db = c_backend_wrapper.CDatabase(':memory:')
        self.st = self.db.get_sync_target()

    def test_attached_to_db(self):
        self.assertEqual(
            self.db._replica_uid, self.st.get_sync_info("misc")[0])

    def test_get_sync_exchange(self):
        exc = self.st._get_sync_exchange("source-uid", 10)
        self.assertIsNot(None, exc)

    def test_sync_exchange_insert_doc_from_source(self):
        exc = self.st._get_sync_exchange("source-uid", 5)
        doc = c_backend_wrapper.make_document('doc-id', 'replica:1',
                tests.simple_doc)
        self.assertEqual([], exc.get_seen_ids())
        exc.insert_doc_from_source(doc, 10, 'T-sid')
        self.assertGetDoc(self.db, 'doc-id', 'replica:1', tests.simple_doc,
                          False)
        self.assertEqual(
            (10, 'T-sid'), self.db._get_replica_gen_and_trans_id('source-uid'))
        self.assertEqual(['doc-id'], exc.get_seen_ids())

    def test_sync_exchange_conflicted_doc(self):
        doc = self.db.create_doc_from_json(tests.simple_doc)
        exc = self.st._get_sync_exchange("source-uid", 5)
        doc2 = c_backend_wrapper.make_document(doc.doc_id, 'replica:1',
                tests.nested_doc)
        self.assertEqual([], exc.get_seen_ids())
        # The insert should be rejected and the doc_id not considered 'seen'
        exc.insert_doc_from_source(doc2, 10, 'T-sid')
        self.assertGetDoc(
            self.db, doc.doc_id, doc.rev, tests.simple_doc, False)
        self.assertEqual([], exc.get_seen_ids())

    def test_sync_exchange_find_doc_ids(self):
        doc = self.db.create_doc_from_json(tests.simple_doc)
        exc = self.st._get_sync_exchange("source-uid", 0)
        self.assertEqual(0, exc.target_gen)
        exc.find_doc_ids_to_return()
        doc_id = exc.get_doc_ids_to_return()[0]
        self.assertEqual(
            (doc.doc_id, 1), doc_id[:-1])
        self.assertTrue(doc_id[-1].startswith('T-'))
        self.assertEqual(1, exc.target_gen)

    def test_sync_exchange_find_doc_ids_not_including_recently_inserted(self):
        doc1 = self.db.create_doc_from_json(tests.simple_doc)
        doc2 = self.db.create_doc_from_json(tests.nested_doc)
        exc = self.st._get_sync_exchange("source-uid", 0)
        doc3 = c_backend_wrapper.make_document(doc1.doc_id,
                doc1.rev + "|zreplica:2", tests.simple_doc)
        exc.insert_doc_from_source(doc3, 10, 'T-sid')
        exc.find_doc_ids_to_return()
        self.assertEqual(
            (doc2.doc_id, 2), exc.get_doc_ids_to_return()[0][:-1])
        self.assertEqual(3, exc.target_gen)

    def test_sync_exchange_return_docs(self):
        returned = []

        def return_doc_cb(doc, gen, trans_id):
            returned.append((doc, gen, trans_id))

        doc1 = self.db.create_doc_from_json(tests.simple_doc)
        exc = self.st._get_sync_exchange("source-uid", 0)
        exc.find_doc_ids_to_return()
        exc.return_docs(return_doc_cb)
        self.assertEqual((doc1, 1), returned[0][:-1])

    def test_sync_exchange_doc_ids(self):
        doc1 = self.db.create_doc_from_json(tests.simple_doc, doc_id='doc-1')
        db2 = c_backend_wrapper.CDatabase(':memory:')
        doc2 = db2.create_doc_from_json(tests.nested_doc, doc_id='doc-2')
        returned = []

        def return_doc_cb(doc, gen, trans_id):
            returned.append((doc, gen, trans_id))

        val = self.st.sync_exchange_doc_ids(
            db2, [(doc2.doc_id, 1, 'T-sid')], 0, None, return_doc_cb)
        last_trans_id = self.db._get_transaction_log()[-1][1]
        self.assertEqual(2, self.db._get_generation())
        self.assertEqual((2, last_trans_id), val)
        self.assertGetDoc(self.db, doc2.doc_id, doc2.rev, tests.nested_doc,
                          False)
        self.assertEqual((doc1, 1), returned[0][:-1])


class TestCHTTPSyncTarget(BackendTests):

    def test_format_sync_url(self):
        target = c_backend_wrapper.create_http_sync_target("http://base_url")
        self.assertEqual("http://base_url/sync-from/replica-uid",
            c_backend_wrapper._format_sync_url(target, "replica-uid"))

    def test_format_sync_url_escapes(self):
        # The base_url should not get munged (we assume it is already a
        # properly formed URL), but the replica-uid should get properly escaped
        target = c_backend_wrapper.create_http_sync_target(
                "http://host/base%2Ctest/")
        self.assertEqual("http://host/base%2Ctest/sync-from/replica%2Cuid",
            c_backend_wrapper._format_sync_url(target, "replica,uid"))

    def test_format_refuses_non_http(self):
        db = c_backend_wrapper.CDatabase(':memory:')
        target = db.get_sync_target()
        self.assertRaises(RuntimeError,
            c_backend_wrapper._format_sync_url, target, 'replica,uid')

    def test_oauth_credentials(self):
        target = c_backend_wrapper.create_oauth_http_sync_target(
                "http://host/base%2Ctest/",
                'consumer-key', 'consumer-secret', 'token-key', 'token-secret')
        auth = c_backend_wrapper._get_oauth_authorization(target,
            "GET", "http://host/base%2Ctest/sync-from/abcd-efg")
        self.assertIsNot(None, auth)
        self.assertTrue(auth.startswith('Authorization: OAuth realm="", '))
        self.assertNotIn('http://host/base', auth)
        self.assertIn('oauth_nonce="', auth)
        self.assertIn('oauth_timestamp="', auth)
        self.assertIn('oauth_consumer_key="consumer-key"', auth)
        self.assertIn('oauth_signature_method="HMAC-SHA1"', auth)
        self.assertIn('oauth_version="1.0"', auth)
        self.assertIn('oauth_token="token-key"', auth)
        self.assertIn('oauth_signature="', auth)


class TestSyncCtoHTTPViaC(tests.TestCaseWithServer):

    make_app_with_state = staticmethod(make_http_app)

    def setUp(self):
        super(TestSyncCtoHTTPViaC, self).setUp()
        if c_backend_wrapper is None:
            self.skipTest("The c_backend_wrapper could not be imported")
        self.startServer()

    def test_trivial_sync(self):
        mem_db = self.request_state._create_database('test.db')
        mem_doc = mem_db.create_doc_from_json(tests.nested_doc)
        url = self.getURL('test.db')
        target = c_backend_wrapper.create_http_sync_target(url)
        db = c_backend_wrapper.CDatabase(':memory:')
        doc = db.create_doc_from_json(tests.simple_doc)
        c_backend_wrapper.sync_db_to_target(db, target)
        self.assertGetDoc(mem_db, doc.doc_id, doc.rev, doc.get_json(), False)
        self.assertGetDoc(db, mem_doc.doc_id, mem_doc.rev, mem_doc.get_json(),
                          False)

    def test_unavailable(self):
        mem_db = self.request_state._create_database('test.db')
        mem_db.create_doc_from_json(tests.nested_doc)
        tries = []

        def wrapper(instance, *args, **kwargs):
            tries.append(None)
            raise errors.Unavailable

        mem_db.whats_changed = wrapper
        url = self.getURL('test.db')
        target = c_backend_wrapper.create_http_sync_target(url)
        db = c_backend_wrapper.CDatabase(':memory:')
        db.create_doc_from_json(tests.simple_doc)
        self.assertRaises(
            errors.Unavailable, c_backend_wrapper.sync_db_to_target, db,
            target)
        self.assertEqual(5, len(tries))

    def test_unavailable_then_available(self):
        mem_db = self.request_state._create_database('test.db')
        mem_doc = mem_db.create_doc_from_json(tests.nested_doc)
        orig_whatschanged = mem_db.whats_changed
        tries = []

        def wrapper(instance, *args, **kwargs):
            if len(tries) < 1:
                tries.append(None)
                raise errors.Unavailable
            return orig_whatschanged(instance, *args, **kwargs)

        mem_db.whats_changed = wrapper
        url = self.getURL('test.db')
        target = c_backend_wrapper.create_http_sync_target(url)
        db = c_backend_wrapper.CDatabase(':memory:')
        doc = db.create_doc_from_json(tests.simple_doc)
        c_backend_wrapper.sync_db_to_target(db, target)
        self.assertEqual(1, len(tries))
        self.assertGetDoc(mem_db, doc.doc_id, doc.rev, doc.get_json(), False)
        self.assertGetDoc(db, mem_doc.doc_id, mem_doc.rev, mem_doc.get_json(),
                          False)

    def test_db_sync(self):
        mem_db = self.request_state._create_database('test.db')
        mem_doc = mem_db.create_doc_from_json(tests.nested_doc)
        url = self.getURL('test.db')
        db = c_backend_wrapper.CDatabase(':memory:')
        doc = db.create_doc_from_json(tests.simple_doc)
        local_gen_before_sync = db.sync(url)
        gen, _, changes = db.whats_changed(local_gen_before_sync)
        self.assertEqual(1, len(changes))
        self.assertEqual(mem_doc.doc_id, changes[0][0])
        self.assertEqual(1, gen - local_gen_before_sync)
        self.assertEqual(1, local_gen_before_sync)
        self.assertGetDoc(mem_db, doc.doc_id, doc.rev, doc.get_json(), False)
        self.assertGetDoc(db, mem_doc.doc_id, mem_doc.rev, mem_doc.get_json(),
                          False)


class TestSyncCtoOAuthHTTPViaC(tests.TestCaseWithServer):

    make_app_with_state = staticmethod(make_oauth_http_app)

    def setUp(self):
        super(TestSyncCtoOAuthHTTPViaC, self).setUp()
        if c_backend_wrapper is None:
            self.skipTest("The c_backend_wrapper could not be imported")
        self.startServer()

    def test_trivial_sync(self):
        mem_db = self.request_state._create_database('test.db')
        mem_doc = mem_db.create_doc_from_json(tests.nested_doc)
        url = self.getURL('~/test.db')
        target = c_backend_wrapper.create_oauth_http_sync_target(url,
                tests.consumer1.key, tests.consumer1.secret,
                tests.token1.key, tests.token1.secret)
        db = c_backend_wrapper.CDatabase(':memory:')
        doc = db.create_doc_from_json(tests.simple_doc)
        c_backend_wrapper.sync_db_to_target(db, target)
        self.assertGetDoc(mem_db, doc.doc_id, doc.rev, doc.get_json(), False)
        self.assertGetDoc(db, mem_doc.doc_id, mem_doc.rev, mem_doc.get_json(),
                          False)


class TestVectorClock(BackendTests):

    def create_vcr(self, rev):
        return c_backend_wrapper.VectorClockRev(rev)

    def test_parse_empty(self):
        self.assertEqual('VectorClockRev()',
                         repr(self.create_vcr('')))

    def test_parse_invalid(self):
        self.assertEqual('VectorClockRev(None)',
                         repr(self.create_vcr('x')))
        self.assertEqual('VectorClockRev(None)',
                         repr(self.create_vcr('x:a')))
        self.assertEqual('VectorClockRev(None)',
                         repr(self.create_vcr('y:1|x:a')))
        self.assertEqual('VectorClockRev(None)',
                         repr(self.create_vcr('x:a|y:1')))
        self.assertEqual('VectorClockRev(None)',
                         repr(self.create_vcr('y:1|x:2a')))
        self.assertEqual('VectorClockRev(None)',
                         repr(self.create_vcr('y:1||')))
        self.assertEqual('VectorClockRev(None)',
                         repr(self.create_vcr('y:1|')))
        self.assertEqual('VectorClockRev(None)',
                         repr(self.create_vcr('y:1|x:2|')))
        self.assertEqual('VectorClockRev(None)',
                         repr(self.create_vcr('y:1|x:2|:')))
        self.assertEqual('VectorClockRev(None)',
                         repr(self.create_vcr('y:1|x:2|m:')))
        self.assertEqual('VectorClockRev(None)',
                         repr(self.create_vcr('y:1|x:|m:3')))
        self.assertEqual('VectorClockRev(None)',
                         repr(self.create_vcr('y:1|:|m:3')))

    def test_parse_single(self):
        self.assertEqual('VectorClockRev(test:1)',
                         repr(self.create_vcr('test:1')))

    def test_parse_multi(self):
        self.assertEqual('VectorClockRev(test:1|z:2)',
                         repr(self.create_vcr('test:1|z:2')))
        self.assertEqual('VectorClockRev(ab:1|bc:2|cd:3|de:4|ef:5)',
                     repr(self.create_vcr('ab:1|bc:2|cd:3|de:4|ef:5')))
        self.assertEqual('VectorClockRev(a:2|b:1)',
                         repr(self.create_vcr('b:1|a:2')))


class TestCDocument(BackendTests):

    def make_document(self, *args, **kwargs):
        return c_backend_wrapper.make_document(*args, **kwargs)

    def test_create(self):
        self.make_document('doc-id', 'uid:1', tests.simple_doc)

    def assertPyDocEqualCDoc(self, *args, **kwargs):
        cdoc = self.make_document(*args, **kwargs)
        pydoc = Document(*args, **kwargs)
        self.assertEqual(pydoc, cdoc)
        self.assertEqual(cdoc, pydoc)

    def test_cmp_to_pydoc_equal(self):
        self.assertPyDocEqualCDoc('doc-id', 'uid:1', tests.simple_doc)
        self.assertPyDocEqualCDoc('doc-id', 'uid:1', tests.simple_doc,
                                  has_conflicts=False)
        self.assertPyDocEqualCDoc('doc-id', 'uid:1', tests.simple_doc,
                                  has_conflicts=True)

    def test_cmp_to_pydoc_not_equal_conflicts(self):
        cdoc = self.make_document('doc-id', 'uid:1', tests.simple_doc)
        pydoc = Document('doc-id', 'uid:1', tests.simple_doc,
                         has_conflicts=True)
        self.assertNotEqual(cdoc, pydoc)
        self.assertNotEqual(pydoc, cdoc)

    def test_cmp_to_pydoc_not_equal_doc_id(self):
        cdoc = self.make_document('doc-id', 'uid:1', tests.simple_doc)
        pydoc = Document('doc2-id', 'uid:1', tests.simple_doc)
        self.assertNotEqual(cdoc, pydoc)
        self.assertNotEqual(pydoc, cdoc)

    def test_cmp_to_pydoc_not_equal_doc_rev(self):
        cdoc = self.make_document('doc-id', 'uid:1', tests.simple_doc)
        pydoc = Document('doc-id', 'uid:2', tests.simple_doc)
        self.assertNotEqual(cdoc, pydoc)
        self.assertNotEqual(pydoc, cdoc)

    def test_cmp_to_pydoc_not_equal_content(self):
        cdoc = self.make_document('doc-id', 'uid:1', tests.simple_doc)
        pydoc = Document('doc-id', 'uid:1', tests.nested_doc)
        self.assertNotEqual(cdoc, pydoc)
        self.assertNotEqual(pydoc, cdoc)


class TestUUID(BackendTests):

    def test_uuid4_conformance(self):
        uuids = set()
        for i in range(20):
            uuid = c_backend_wrapper.generate_hex_uuid()
            self.assertIsInstance(uuid, str)
            self.assertEqual(32, len(uuid))
            # This will raise ValueError if it isn't a valid hex string
            long(uuid, 16)
            # Version 4 uuids have 2 other requirements, the high 4 bits of the
            # seventh byte are always '0x4', and the middle bits of byte 9 are
            # always set
            self.assertEqual('4', uuid[12])
            self.assertTrue(uuid[16] in '89ab')
            self.assertTrue(uuid not in uuids)
            uuids.add(uuid)
