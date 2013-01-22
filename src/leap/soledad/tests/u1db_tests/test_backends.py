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

"""The backend class for U1DB. This deals with hiding storage details."""

try:
    import simplejson as json
except ImportError:
    import json  # noqa
from u1db import (
    DocumentBase,
    errors,
    vectorclock,
    )

from leap.soledad.tests import u1db_tests as tests

simple_doc = tests.simple_doc
nested_doc = tests.nested_doc

from leap.soledad.tests.u1db_tests.test_remote_sync_target import (
    make_http_app,
    make_oauth_http_app,
)

from u1db.remote import (
    http_database,
    )

try:
    from u1db.tests import c_backend_wrapper
except ImportError:
    c_backend_wrapper = None  # noqa


def make_http_database_for_test(test, replica_uid, path='test'):
    test.startServer()
    test.request_state._create_database(replica_uid)
    return http_database.HTTPDatabase(test.getURL(path))


def copy_http_database_for_test(test, db):
    # DO NOT COPY OR REUSE THIS CODE OUTSIDE TESTS: COPYING U1DB DATABASES IS
    # THE WRONG THING TO DO, THE ONLY REASON WE DO SO HERE IS TO TEST THAT WE
    # CORRECTLY DETECT IT HAPPENING SO THAT WE CAN RAISE ERRORS RATHER THAN
    # CORRUPT USER DATA. USE SYNC INSTEAD, OR WE WILL SEND NINJA TO YOUR
    # HOUSE.
    return test.request_state._copy_database(db)


def make_oauth_http_database_for_test(test, replica_uid):
    http_db = make_http_database_for_test(test, replica_uid, '~/test')
    http_db.set_oauth_credentials(tests.consumer1.key, tests.consumer1.secret,
                                  tests.token1.key, tests.token1.secret)
    return http_db


def copy_oauth_http_database_for_test(test, db):
    # DO NOT COPY OR REUSE THIS CODE OUTSIDE TESTS: COPYING U1DB DATABASES IS
    # THE WRONG THING TO DO, THE ONLY REASON WE DO SO HERE IS TO TEST THAT WE
    # CORRECTLY DETECT IT HAPPENING SO THAT WE CAN RAISE ERRORS RATHER THAN
    # CORRUPT USER DATA. USE SYNC INSTEAD, OR WE WILL SEND NINJA TO YOUR
    # HOUSE.
    http_db = test.request_state._copy_database(db)
    http_db.set_oauth_credentials(tests.consumer1.key, tests.consumer1.secret,
                                  tests.token1.key, tests.token1.secret)
    return http_db


class TestAlternativeDocument(DocumentBase):
    """A (not very) alternative implementation of Document."""


class AllDatabaseTests(tests.DatabaseBaseTests, tests.TestCaseWithServer):

    scenarios = tests.LOCAL_DATABASES_SCENARIOS + [
        ('http', {'make_database_for_test': make_http_database_for_test,
                  'copy_database_for_test': copy_http_database_for_test,
                  'make_document_for_test': tests.make_document_for_test,
                  'make_app_with_state': make_http_app}),
        ('oauth_http', {'make_database_for_test':
                        make_oauth_http_database_for_test,
                        'copy_database_for_test':
                        copy_oauth_http_database_for_test,
                        'make_document_for_test': tests.make_document_for_test,
                        'make_app_with_state': make_oauth_http_app})
        ] #+ tests.C_DATABASE_SCENARIOS

    def test_close(self):
        self.db.close()

    def test_create_doc_allocating_doc_id(self):
        doc = self.db.create_doc_from_json(simple_doc)
        self.assertNotEqual(None, doc.doc_id)
        self.assertNotEqual(None, doc.rev)
        self.assertGetDoc(self.db, doc.doc_id, doc.rev, simple_doc, False)

    def test_create_doc_different_ids_same_db(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        doc2 = self.db.create_doc_from_json(nested_doc)
        self.assertNotEqual(doc1.doc_id, doc2.doc_id)

    def test_create_doc_with_id(self):
        doc = self.db.create_doc_from_json(simple_doc, doc_id='my-id')
        self.assertEqual('my-id', doc.doc_id)
        self.assertNotEqual(None, doc.rev)
        self.assertGetDoc(self.db, doc.doc_id, doc.rev, simple_doc, False)

    def test_create_doc_existing_id(self):
        doc = self.db.create_doc_from_json(simple_doc)
        new_content = '{"something": "else"}'
        self.assertRaises(
            errors.RevisionConflict, self.db.create_doc_from_json,
            new_content, doc.doc_id)
        self.assertGetDoc(self.db, doc.doc_id, doc.rev, simple_doc, False)

    def test_put_doc_creating_initial(self):
        doc = self.make_document('my_doc_id', None, simple_doc)
        new_rev = self.db.put_doc(doc)
        self.assertIsNot(None, new_rev)
        self.assertGetDoc(self.db, 'my_doc_id', new_rev, simple_doc, False)

    def test_put_doc_space_in_id(self):
        doc = self.make_document('my doc id', None, simple_doc)
        self.assertRaises(errors.InvalidDocId, self.db.put_doc, doc)

    def test_put_doc_update(self):
        doc = self.db.create_doc_from_json(simple_doc, doc_id='my_doc_id')
        orig_rev = doc.rev
        doc.set_json('{"updated": "stuff"}')
        new_rev = self.db.put_doc(doc)
        self.assertNotEqual(new_rev, orig_rev)
        self.assertGetDoc(self.db, 'my_doc_id', new_rev,
                          '{"updated": "stuff"}', False)
        self.assertEqual(doc.rev, new_rev)

    def test_put_non_ascii_key(self):
        content = json.dumps({u'key\xe5': u'val'})
        doc = self.db.create_doc_from_json(content, doc_id='my_doc')
        self.assertGetDoc(self.db, 'my_doc', doc.rev, content, False)

    def test_put_non_ascii_value(self):
        content = json.dumps({'key': u'\xe5'})
        doc = self.db.create_doc_from_json(content, doc_id='my_doc')
        self.assertGetDoc(self.db, 'my_doc', doc.rev, content, False)

    def test_put_doc_refuses_no_id(self):
        doc = self.make_document(None, None, simple_doc)
        self.assertRaises(errors.InvalidDocId, self.db.put_doc, doc)
        doc = self.make_document("", None, simple_doc)
        self.assertRaises(errors.InvalidDocId, self.db.put_doc, doc)

    def test_put_doc_refuses_slashes(self):
        doc = self.make_document('a/b', None, simple_doc)
        self.assertRaises(errors.InvalidDocId, self.db.put_doc, doc)
        doc = self.make_document(r'\b', None, simple_doc)
        self.assertRaises(errors.InvalidDocId, self.db.put_doc, doc)

    def test_put_doc_url_quoting_is_fine(self):
        doc_id = "%2F%2Ffoo%2Fbar"
        doc = self.make_document(doc_id, None, simple_doc)
        new_rev = self.db.put_doc(doc)
        self.assertGetDoc(self.db, doc_id, new_rev, simple_doc, False)

    def test_put_doc_refuses_non_existing_old_rev(self):
        doc = self.make_document('doc-id', 'test:4', simple_doc)
        self.assertRaises(errors.RevisionConflict, self.db.put_doc, doc)

    def test_put_doc_refuses_non_ascii_doc_id(self):
        doc = self.make_document('d\xc3\xa5c-id', None, simple_doc)
        self.assertRaises(errors.InvalidDocId, self.db.put_doc, doc)

    def test_put_fails_with_bad_old_rev(self):
        doc = self.db.create_doc_from_json(simple_doc, doc_id='my_doc_id')
        old_rev = doc.rev
        bad_doc = self.make_document(doc.doc_id, 'other:1',
                                     '{"something": "else"}')
        self.assertRaises(errors.RevisionConflict, self.db.put_doc, bad_doc)
        self.assertGetDoc(self.db, 'my_doc_id', old_rev, simple_doc, False)

    def test_create_succeeds_after_delete(self):
        doc = self.db.create_doc_from_json(simple_doc, doc_id='my_doc_id')
        self.db.delete_doc(doc)
        deleted_doc = self.db.get_doc('my_doc_id', include_deleted=True)
        deleted_vc = vectorclock.VectorClockRev(deleted_doc.rev)
        new_doc = self.db.create_doc_from_json(simple_doc, doc_id='my_doc_id')
        self.assertGetDoc(self.db, 'my_doc_id', new_doc.rev, simple_doc, False)
        new_vc = vectorclock.VectorClockRev(new_doc.rev)
        self.assertTrue(
            new_vc.is_newer(deleted_vc),
            "%s does not supersede %s" % (new_doc.rev, deleted_doc.rev))

    def test_put_succeeds_after_delete(self):
        doc = self.db.create_doc_from_json(simple_doc, doc_id='my_doc_id')
        self.db.delete_doc(doc)
        deleted_doc = self.db.get_doc('my_doc_id', include_deleted=True)
        deleted_vc = vectorclock.VectorClockRev(deleted_doc.rev)
        doc2 = self.make_document('my_doc_id', None, simple_doc)
        self.db.put_doc(doc2)
        self.assertGetDoc(self.db, 'my_doc_id', doc2.rev, simple_doc, False)
        new_vc = vectorclock.VectorClockRev(doc2.rev)
        self.assertTrue(
            new_vc.is_newer(deleted_vc),
            "%s does not supersede %s" % (doc2.rev, deleted_doc.rev))

    def test_get_doc_after_put(self):
        doc = self.db.create_doc_from_json(simple_doc, doc_id='my_doc_id')
        self.assertGetDoc(self.db, 'my_doc_id', doc.rev, simple_doc, False)

    def test_get_doc_nonexisting(self):
        self.assertIs(None, self.db.get_doc('non-existing'))

    def test_get_doc_deleted(self):
        doc = self.db.create_doc_from_json(simple_doc, doc_id='my_doc_id')
        self.db.delete_doc(doc)
        self.assertIs(None, self.db.get_doc('my_doc_id'))

    def test_get_doc_include_deleted(self):
        doc = self.db.create_doc_from_json(simple_doc, doc_id='my_doc_id')
        self.db.delete_doc(doc)
        self.assertGetDocIncludeDeleted(
            self.db, doc.doc_id, doc.rev, None, False)

    def test_get_docs(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        doc2 = self.db.create_doc_from_json(nested_doc)
        self.assertEqual([doc1, doc2],
                         list(self.db.get_docs([doc1.doc_id, doc2.doc_id])))

    def test_get_docs_deleted(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        doc2 = self.db.create_doc_from_json(nested_doc)
        self.db.delete_doc(doc1)
        self.assertEqual([doc2],
                         list(self.db.get_docs([doc1.doc_id, doc2.doc_id])))

    def test_get_docs_include_deleted(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        doc2 = self.db.create_doc_from_json(nested_doc)
        self.db.delete_doc(doc1)
        self.assertEqual(
            [doc1, doc2],
            list(self.db.get_docs([doc1.doc_id, doc2.doc_id],
                                  include_deleted=True)))

    def test_get_docs_request_ordered(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        doc2 = self.db.create_doc_from_json(nested_doc)
        self.assertEqual([doc1, doc2],
                         list(self.db.get_docs([doc1.doc_id, doc2.doc_id])))
        self.assertEqual([doc2, doc1],
                         list(self.db.get_docs([doc2.doc_id, doc1.doc_id])))

    def test_get_docs_empty_list(self):
        self.assertEqual([], list(self.db.get_docs([])))

    def test_handles_nested_content(self):
        doc = self.db.create_doc_from_json(nested_doc)
        self.assertGetDoc(self.db, doc.doc_id, doc.rev, nested_doc, False)

    def test_handles_doc_with_null(self):
        doc = self.db.create_doc_from_json('{"key": null}')
        self.assertGetDoc(self.db, doc.doc_id, doc.rev, '{"key": null}', False)

    def test_delete_doc(self):
        doc = self.db.create_doc_from_json(simple_doc)
        self.assertGetDoc(self.db, doc.doc_id, doc.rev, simple_doc, False)
        orig_rev = doc.rev
        self.db.delete_doc(doc)
        self.assertNotEqual(orig_rev, doc.rev)
        self.assertGetDocIncludeDeleted(
            self.db, doc.doc_id, doc.rev, None, False)
        self.assertIs(None, self.db.get_doc(doc.doc_id))

    def test_delete_doc_non_existent(self):
        doc = self.make_document('non-existing', 'other:1', simple_doc)
        self.assertRaises(errors.DocumentDoesNotExist, self.db.delete_doc, doc)

    def test_delete_doc_already_deleted(self):
        doc = self.db.create_doc_from_json(simple_doc)
        self.db.delete_doc(doc)
        self.assertRaises(errors.DocumentAlreadyDeleted,
                          self.db.delete_doc, doc)
        self.assertGetDocIncludeDeleted(
            self.db, doc.doc_id, doc.rev, None, False)

    def test_delete_doc_bad_rev(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        self.assertGetDoc(self.db, doc1.doc_id, doc1.rev, simple_doc, False)
        doc2 = self.make_document(doc1.doc_id, 'other:1', simple_doc)
        self.assertRaises(errors.RevisionConflict, self.db.delete_doc, doc2)
        self.assertGetDoc(self.db, doc1.doc_id, doc1.rev, simple_doc, False)

    def test_delete_doc_sets_content_to_None(self):
        doc = self.db.create_doc_from_json(simple_doc)
        self.db.delete_doc(doc)
        self.assertIs(None, doc.get_json())

    def test_delete_doc_rev_supersedes(self):
        doc = self.db.create_doc_from_json(simple_doc)
        doc.set_json(nested_doc)
        self.db.put_doc(doc)
        doc.set_json('{"fishy": "content"}')
        self.db.put_doc(doc)
        old_rev = doc.rev
        self.db.delete_doc(doc)
        cur_vc = vectorclock.VectorClockRev(old_rev)
        deleted_vc = vectorclock.VectorClockRev(doc.rev)
        self.assertTrue(deleted_vc.is_newer(cur_vc),
                "%s does not supersede %s" % (doc.rev, old_rev))

    def test_delete_then_put(self):
        doc = self.db.create_doc_from_json(simple_doc)
        self.db.delete_doc(doc)
        self.assertGetDocIncludeDeleted(
            self.db, doc.doc_id, doc.rev, None, False)
        doc.set_json(nested_doc)
        self.db.put_doc(doc)
        self.assertGetDoc(self.db, doc.doc_id, doc.rev, nested_doc, False)


class DocumentSizeTests(tests.DatabaseBaseTests):

    scenarios = tests.LOCAL_DATABASES_SCENARIOS #+ tests.C_DATABASE_SCENARIOS

    def test_put_doc_refuses_oversized_documents(self):
        self.db.set_document_size_limit(1)
        doc = self.make_document('doc-id', None, simple_doc)
        self.assertRaises(errors.DocumentTooBig, self.db.put_doc, doc)

    def test_create_doc_refuses_oversized_documents(self):
        self.db.set_document_size_limit(1)
        self.assertRaises(
            errors.DocumentTooBig, self.db.create_doc_from_json, simple_doc,
            doc_id='my_doc_id')

    def test_set_document_size_limit_zero(self):
        self.db.set_document_size_limit(0)
        self.assertEqual(0, self.db.document_size_limit)

    def test_set_document_size_limit(self):
        self.db.set_document_size_limit(1000000)
        self.assertEqual(1000000, self.db.document_size_limit)


class LocalDatabaseTests(tests.DatabaseBaseTests):

    scenarios = tests.LOCAL_DATABASES_SCENARIOS #+ tests.C_DATABASE_SCENARIOS

    def test_create_doc_different_ids_diff_db(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        db2 = self.create_database('other-uid')
        doc2 = db2.create_doc_from_json(simple_doc)
        self.assertNotEqual(doc1.doc_id, doc2.doc_id)

    def test_put_doc_refuses_slashes_picky(self):
        doc = self.make_document('/a', None, simple_doc)
        self.assertRaises(errors.InvalidDocId, self.db.put_doc, doc)

    def test_get_all_docs_empty(self):
        self.assertEqual([], list(self.db.get_all_docs()[1]))

    def test_get_all_docs(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        doc2 = self.db.create_doc_from_json(nested_doc)
        self.assertEqual(
            sorted([doc1, doc2]), sorted(list(self.db.get_all_docs()[1])))

    def test_get_all_docs_exclude_deleted(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        doc2 = self.db.create_doc_from_json(nested_doc)
        self.db.delete_doc(doc2)
        self.assertEqual([doc1], list(self.db.get_all_docs()[1]))

    def test_get_all_docs_include_deleted(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        doc2 = self.db.create_doc_from_json(nested_doc)
        self.db.delete_doc(doc2)
        self.assertEqual(
            sorted([doc1, doc2]),
            sorted(list(self.db.get_all_docs(include_deleted=True)[1])))

    def test_get_all_docs_generation(self):
        self.db.create_doc_from_json(simple_doc)
        self.db.create_doc_from_json(nested_doc)
        self.assertEqual(2, self.db.get_all_docs()[0])

    def test_simple_put_doc_if_newer(self):
        doc = self.make_document('my-doc-id', 'test:1', simple_doc)
        state_at_gen = self.db._put_doc_if_newer(
            doc, save_conflict=False, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        self.assertEqual(('inserted', 1), state_at_gen)
        self.assertGetDoc(self.db, 'my-doc-id', 'test:1', simple_doc, False)

    def test_simple_put_doc_if_newer_deleted(self):
        self.db.create_doc_from_json('{}', doc_id='my-doc-id')
        doc = self.make_document('my-doc-id', 'test:2', None)
        state_at_gen = self.db._put_doc_if_newer(
            doc, save_conflict=False, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        self.assertEqual(('inserted', 2), state_at_gen)
        self.assertGetDocIncludeDeleted(
            self.db, 'my-doc-id', 'test:2', None, False)

    def test_put_doc_if_newer_already_superseded(self):
        orig_doc = '{"new": "doc"}'
        doc1 = self.db.create_doc_from_json(orig_doc)
        doc1_rev1 = doc1.rev
        doc1.set_json(simple_doc)
        self.db.put_doc(doc1)
        doc1_rev2 = doc1.rev
        # Nothing is inserted, because the document is already superseded
        doc = self.make_document(doc1.doc_id, doc1_rev1, orig_doc)
        state, _ = self.db._put_doc_if_newer(
            doc, save_conflict=False, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        self.assertEqual('superseded', state)
        self.assertGetDoc(self.db, doc1.doc_id, doc1_rev2, simple_doc, False)

    def test_put_doc_if_newer_autoresolve(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        rev = doc1.rev
        doc = self.make_document(doc1.doc_id, "whatever:1", doc1.get_json())
        state, _ = self.db._put_doc_if_newer(
            doc, save_conflict=False, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        self.assertEqual('superseded', state)
        doc2 = self.db.get_doc(doc1.doc_id)
        v2 = vectorclock.VectorClockRev(doc2.rev)
        self.assertTrue(v2.is_newer(vectorclock.VectorClockRev("whatever:1")))
        self.assertTrue(v2.is_newer(vectorclock.VectorClockRev(rev)))
        # strictly newer locally
        self.assertTrue(rev not in doc2.rev)

    def test_put_doc_if_newer_already_converged(self):
        orig_doc = '{"new": "doc"}'
        doc1 = self.db.create_doc_from_json(orig_doc)
        state_at_gen = self.db._put_doc_if_newer(
            doc1, save_conflict=False, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        self.assertEqual(('converged', 1), state_at_gen)

    def test_put_doc_if_newer_conflicted(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        # Nothing is inserted, the document id is returned as would-conflict
        alt_doc = self.make_document(doc1.doc_id, 'alternate:1', nested_doc)
        state, _ = self.db._put_doc_if_newer(
            alt_doc, save_conflict=False, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        self.assertEqual('conflicted', state)
        # The database wasn't altered
        self.assertGetDoc(self.db, doc1.doc_id, doc1.rev, simple_doc, False)

    def test_put_doc_if_newer_newer_generation(self):
        self.db._set_replica_gen_and_trans_id('other', 1, 'T-sid')
        doc = self.make_document('doc_id', 'other:2', simple_doc)
        state, _ = self.db._put_doc_if_newer(
            doc, save_conflict=False, replica_uid='other', replica_gen=2,
            replica_trans_id='T-irrelevant')
        self.assertEqual('inserted', state)

    def test_put_doc_if_newer_same_generation_same_txid(self):
        self.db._set_replica_gen_and_trans_id('other', 1, 'T-sid')
        doc = self.db.create_doc_from_json(simple_doc)
        self.make_document(doc.doc_id, 'other:1', simple_doc)
        state, _ = self.db._put_doc_if_newer(
            doc, save_conflict=False, replica_uid='other', replica_gen=1,
            replica_trans_id='T-sid')
        self.assertEqual('converged', state)

    def test_put_doc_if_newer_wrong_transaction_id(self):
        self.db._set_replica_gen_and_trans_id('other', 1, 'T-sid')
        doc = self.make_document('doc_id', 'other:1', simple_doc)
        self.assertRaises(
            errors.InvalidTransactionId,
            self.db._put_doc_if_newer, doc, save_conflict=False,
            replica_uid='other', replica_gen=1, replica_trans_id='T-sad')

    def test_put_doc_if_newer_old_generation_older_doc(self):
        orig_doc = '{"new": "doc"}'
        doc = self.db.create_doc_from_json(orig_doc)
        doc_rev1 = doc.rev
        doc.set_json(simple_doc)
        self.db.put_doc(doc)
        self.db._set_replica_gen_and_trans_id('other', 3, 'T-sid')
        older_doc = self.make_document(doc.doc_id, doc_rev1, simple_doc)
        state, _ = self.db._put_doc_if_newer(
            older_doc, save_conflict=False, replica_uid='other', replica_gen=8,
            replica_trans_id='T-irrelevant')
        self.assertEqual('superseded', state)

    def test_put_doc_if_newer_old_generation_newer_doc(self):
        self.db._set_replica_gen_and_trans_id('other', 5, 'T-sid')
        doc = self.make_document('doc_id', 'other:1', simple_doc)
        self.assertRaises(
            errors.InvalidGeneration,
            self.db._put_doc_if_newer, doc, save_conflict=False,
            replica_uid='other', replica_gen=1, replica_trans_id='T-sad')

    def test_put_doc_if_newer_replica_uid(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        self.db._set_replica_gen_and_trans_id('other', 1, 'T-sid')
        doc2 = self.make_document(doc1.doc_id, doc1.rev + '|other:1',
                                  nested_doc)
        self.assertEqual('inserted',
            self.db._put_doc_if_newer(doc2, save_conflict=False,
                                      replica_uid='other', replica_gen=2,
                                      replica_trans_id='T-id2')[0])
        self.assertEqual((2, 'T-id2'), self.db._get_replica_gen_and_trans_id(
            'other'))
        # Compare to the old rev, should be superseded
        doc2 = self.make_document(doc1.doc_id, doc1.rev, nested_doc)
        self.assertEqual('superseded',
            self.db._put_doc_if_newer(doc2, save_conflict=False,
                                      replica_uid='other', replica_gen=3,
                                      replica_trans_id='T-id3')[0])
        self.assertEqual(
            (3, 'T-id3'), self.db._get_replica_gen_and_trans_id('other'))
        # A conflict that isn't saved still records the sync gen, because we
        # don't need to see it again
        doc2 = self.make_document(doc1.doc_id, doc1.rev + '|fourth:1',
                                  '{}')
        self.assertEqual('conflicted',
            self.db._put_doc_if_newer(doc2, save_conflict=False,
                                      replica_uid='other', replica_gen=4,
                                      replica_trans_id='T-id4')[0])
        self.assertEqual(
            (4, 'T-id4'), self.db._get_replica_gen_and_trans_id('other'))

    def test__get_replica_gen_and_trans_id(self):
        self.assertEqual(
            (0, ''), self.db._get_replica_gen_and_trans_id('other-db'))
        self.db._set_replica_gen_and_trans_id('other-db', 2, 'T-transaction')
        self.assertEqual(
            (2, 'T-transaction'),
            self.db._get_replica_gen_and_trans_id('other-db'))

    def test_put_updates_transaction_log(self):
        doc = self.db.create_doc_from_json(simple_doc)
        self.assertTransactionLog([doc.doc_id], self.db)
        doc.set_json('{"something": "else"}')
        self.db.put_doc(doc)
        self.assertTransactionLog([doc.doc_id, doc.doc_id], self.db)
        last_trans_id = self.getLastTransId(self.db)
        self.assertEqual((2, last_trans_id, [(doc.doc_id, 2, last_trans_id)]),
                         self.db.whats_changed())

    def test_delete_updates_transaction_log(self):
        doc = self.db.create_doc_from_json(simple_doc)
        db_gen, _, _ = self.db.whats_changed()
        self.db.delete_doc(doc)
        last_trans_id = self.getLastTransId(self.db)
        self.assertEqual((2, last_trans_id, [(doc.doc_id, 2, last_trans_id)]),
                         self.db.whats_changed(db_gen))

    def test_whats_changed_initial_database(self):
        self.assertEqual((0, '', []), self.db.whats_changed())

    def test_whats_changed_returns_one_id_for_multiple_changes(self):
        doc = self.db.create_doc_from_json(simple_doc)
        doc.set_json('{"new": "contents"}')
        self.db.put_doc(doc)
        last_trans_id = self.getLastTransId(self.db)
        self.assertEqual((2, last_trans_id, [(doc.doc_id, 2, last_trans_id)]),
                         self.db.whats_changed())
        self.assertEqual((2, last_trans_id, []), self.db.whats_changed(2))

    def test_whats_changed_returns_last_edits_ascending(self):
        doc = self.db.create_doc_from_json(simple_doc)
        doc1 = self.db.create_doc_from_json(simple_doc)
        doc.set_json('{"new": "contents"}')
        self.db.delete_doc(doc1)
        delete_trans_id = self.getLastTransId(self.db)
        self.db.put_doc(doc)
        put_trans_id = self.getLastTransId(self.db)
        self.assertEqual((4, put_trans_id,
                          [(doc1.doc_id, 3, delete_trans_id),
                           (doc.doc_id, 4, put_trans_id)]),
                         self.db.whats_changed())

    def test_whats_changed_doesnt_include_old_gen(self):
        self.db.create_doc_from_json(simple_doc)
        self.db.create_doc_from_json(simple_doc)
        doc2 = self.db.create_doc_from_json(simple_doc)
        last_trans_id = self.getLastTransId(self.db)
        self.assertEqual((3, last_trans_id, [(doc2.doc_id, 3, last_trans_id)]),
                         self.db.whats_changed(2))


class LocalDatabaseValidateGenNTransIdTests(tests.DatabaseBaseTests):

    scenarios = tests.LOCAL_DATABASES_SCENARIOS #+ tests.C_DATABASE_SCENARIOS

    def test_validate_gen_and_trans_id(self):
        self.db.create_doc_from_json(simple_doc)
        gen, trans_id = self.db._get_generation_info()
        self.db.validate_gen_and_trans_id(gen, trans_id)

    def test_validate_gen_and_trans_id_invalid_txid(self):
        self.db.create_doc_from_json(simple_doc)
        gen, _ = self.db._get_generation_info()
        self.assertRaises(
            errors.InvalidTransactionId,
            self.db.validate_gen_and_trans_id, gen, 'wrong')

    def test_validate_gen_and_trans_id_invalid_gen(self):
        self.db.create_doc_from_json(simple_doc)
        gen, trans_id = self.db._get_generation_info()
        self.assertRaises(
            errors.InvalidGeneration,
            self.db.validate_gen_and_trans_id, gen + 1, trans_id)


class LocalDatabaseValidateSourceGenTests(tests.DatabaseBaseTests):

    scenarios = tests.LOCAL_DATABASES_SCENARIOS #+ tests.C_DATABASE_SCENARIOS

    def test_validate_source_gen_and_trans_id_same(self):
        self.db._set_replica_gen_and_trans_id('other', 1, 'T-sid')
        self.db._validate_source('other', 1, 'T-sid')

    def test_validate_source_gen_newer(self):
        self.db._set_replica_gen_and_trans_id('other', 1, 'T-sid')
        self.db._validate_source('other', 2, 'T-whatevs')

    def test_validate_source_wrong_txid(self):
        self.db._set_replica_gen_and_trans_id('other', 1, 'T-sid')
        self.assertRaises(
            errors.InvalidTransactionId,
            self.db._validate_source, 'other', 1, 'T-sad')


class LocalDatabaseWithConflictsTests(tests.DatabaseBaseTests):
    # test supporting/functionality around storing conflicts

    scenarios = tests.LOCAL_DATABASES_SCENARIOS #+ tests.C_DATABASE_SCENARIOS

    def test_get_docs_conflicted(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        doc2 = self.make_document(doc1.doc_id, 'alternate:1', nested_doc)
        self.db._put_doc_if_newer(
            doc2, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        self.assertEqual([doc2], list(self.db.get_docs([doc1.doc_id])))

    def test_get_docs_conflicts_ignored(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        doc2 = self.db.create_doc_from_json(nested_doc)
        alt_doc = self.make_document(doc1.doc_id, 'alternate:1', nested_doc)
        self.db._put_doc_if_newer(
            alt_doc, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        no_conflict_doc = self.make_document(doc1.doc_id, 'alternate:1',
                                             nested_doc)
        self.assertEqual([no_conflict_doc, doc2],
                         list(self.db.get_docs([doc1.doc_id, doc2.doc_id],
                                          check_for_conflicts=False)))

    def test_get_doc_conflicts(self):
        doc = self.db.create_doc_from_json(simple_doc)
        alt_doc = self.make_document(doc.doc_id, 'alternate:1', nested_doc)
        self.db._put_doc_if_newer(
            alt_doc, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        self.assertEqual([alt_doc, doc],
                         self.db.get_doc_conflicts(doc.doc_id))

    def test_get_all_docs_sees_conflicts(self):
        doc = self.db.create_doc_from_json(simple_doc)
        alt_doc = self.make_document(doc.doc_id, 'alternate:1', nested_doc)
        self.db._put_doc_if_newer(
            alt_doc, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        _, docs = self.db.get_all_docs()
        self.assertTrue(list(docs)[0].has_conflicts)

    def test_get_doc_conflicts_unconflicted(self):
        doc = self.db.create_doc_from_json(simple_doc)
        self.assertEqual([], self.db.get_doc_conflicts(doc.doc_id))

    def test_get_doc_conflicts_no_such_id(self):
        self.assertEqual([], self.db.get_doc_conflicts('doc-id'))

    def test_resolve_doc(self):
        doc = self.db.create_doc_from_json(simple_doc)
        alt_doc = self.make_document(doc.doc_id, 'alternate:1', nested_doc)
        self.db._put_doc_if_newer(
            alt_doc, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        self.assertGetDocConflicts(self.db, doc.doc_id,
            [('alternate:1', nested_doc), (doc.rev, simple_doc)])
        orig_rev = doc.rev
        self.db.resolve_doc(doc, [alt_doc.rev, doc.rev])
        self.assertNotEqual(orig_rev, doc.rev)
        self.assertFalse(doc.has_conflicts)
        self.assertGetDoc(self.db, doc.doc_id, doc.rev, simple_doc, False)
        self.assertGetDocConflicts(self.db, doc.doc_id, [])

    def test_resolve_doc_picks_biggest_vcr(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        doc2 = self.make_document(doc1.doc_id, 'alternate:1', nested_doc)
        self.db._put_doc_if_newer(
            doc2, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        self.assertGetDocConflicts(self.db, doc1.doc_id,
                                   [(doc2.rev, nested_doc),
                                    (doc1.rev, simple_doc)])
        orig_doc1_rev = doc1.rev
        self.db.resolve_doc(doc1, [doc2.rev, doc1.rev])
        self.assertFalse(doc1.has_conflicts)
        self.assertNotEqual(orig_doc1_rev, doc1.rev)
        self.assertGetDoc(self.db, doc1.doc_id, doc1.rev, simple_doc, False)
        self.assertGetDocConflicts(self.db, doc1.doc_id, [])
        vcr_1 = vectorclock.VectorClockRev(orig_doc1_rev)
        vcr_2 = vectorclock.VectorClockRev(doc2.rev)
        vcr_new = vectorclock.VectorClockRev(doc1.rev)
        self.assertTrue(vcr_new.is_newer(vcr_1))
        self.assertTrue(vcr_new.is_newer(vcr_2))

    def test_resolve_doc_partial_not_winning(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        doc2 = self.make_document(doc1.doc_id, 'alternate:1', nested_doc)
        self.db._put_doc_if_newer(
            doc2, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        self.assertGetDocConflicts(self.db, doc1.doc_id,
                                   [(doc2.rev, nested_doc),
                                    (doc1.rev, simple_doc)])
        content3 = '{"key": "valin3"}'
        doc3 = self.make_document(doc1.doc_id, 'third:1', content3)
        self.db._put_doc_if_newer(
            doc3, save_conflict=True, replica_uid='r', replica_gen=2,
            replica_trans_id='bar')
        self.assertGetDocConflicts(self.db, doc1.doc_id,
            [(doc3.rev, content3),
             (doc1.rev, simple_doc),
             (doc2.rev, nested_doc)])
        self.db.resolve_doc(doc1, [doc2.rev, doc1.rev])
        self.assertTrue(doc1.has_conflicts)
        self.assertGetDoc(self.db, doc1.doc_id, doc3.rev, content3, True)
        self.assertGetDocConflicts(self.db, doc1.doc_id,
            [(doc3.rev, content3),
             (doc1.rev, simple_doc)])

    def test_resolve_doc_partial_winning(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        doc2 = self.make_document(doc1.doc_id, 'alternate:1', nested_doc)
        self.db._put_doc_if_newer(
            doc2, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        content3 = '{"key": "valin3"}'
        doc3 = self.make_document(doc1.doc_id, 'third:1', content3)
        self.db._put_doc_if_newer(
            doc3, save_conflict=True, replica_uid='r', replica_gen=2,
            replica_trans_id='bar')
        self.assertGetDocConflicts(self.db, doc1.doc_id,
                                   [(doc3.rev, content3),
                                    (doc1.rev, simple_doc),
                                    (doc2.rev, nested_doc)])
        self.db.resolve_doc(doc1, [doc3.rev, doc1.rev])
        self.assertTrue(doc1.has_conflicts)
        self.assertGetDocConflicts(self.db, doc1.doc_id,
                                   [(doc1.rev, simple_doc),
                                    (doc2.rev, nested_doc)])

    def test_resolve_doc_with_delete_conflict(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        self.db.delete_doc(doc1)
        doc2 = self.make_document(doc1.doc_id, 'alternate:1', nested_doc)
        self.db._put_doc_if_newer(
            doc2, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        self.assertGetDocConflicts(self.db, doc1.doc_id,
                                   [(doc2.rev, nested_doc),
                                    (doc1.rev, None)])
        self.db.resolve_doc(doc2, [doc1.rev, doc2.rev])
        self.assertGetDocConflicts(self.db, doc1.doc_id, [])
        self.assertGetDoc(self.db, doc2.doc_id, doc2.rev, nested_doc, False)

    def test_resolve_doc_with_delete_to_delete(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        self.db.delete_doc(doc1)
        doc2 = self.make_document(doc1.doc_id, 'alternate:1', nested_doc)
        self.db._put_doc_if_newer(
            doc2, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        self.assertGetDocConflicts(self.db, doc1.doc_id,
                                   [(doc2.rev, nested_doc),
                                    (doc1.rev, None)])
        self.db.resolve_doc(doc1, [doc1.rev, doc2.rev])
        self.assertGetDocConflicts(self.db, doc1.doc_id, [])
        self.assertGetDocIncludeDeleted(
            self.db, doc1.doc_id, doc1.rev, None, False)

    def test_put_doc_if_newer_save_conflicted(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        # Document is inserted as a conflict
        doc2 = self.make_document(doc1.doc_id, 'alternate:1', nested_doc)
        state, _ = self.db._put_doc_if_newer(
            doc2, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        self.assertEqual('conflicted', state)
        # The database was updated
        self.assertGetDoc(self.db, doc1.doc_id, doc2.rev, nested_doc, True)

    def test_force_doc_conflict_supersedes_properly(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        doc2 = self.make_document(doc1.doc_id, 'alternate:1', '{"b": 1}')
        self.db._put_doc_if_newer(
            doc2, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        doc3 = self.make_document(doc1.doc_id, 'altalt:1', '{"c": 1}')
        self.db._put_doc_if_newer(
            doc3, save_conflict=True, replica_uid='r', replica_gen=2,
            replica_trans_id='bar')
        doc22 = self.make_document(doc1.doc_id, 'alternate:2', '{"b": 2}')
        self.db._put_doc_if_newer(
            doc22, save_conflict=True, replica_uid='r', replica_gen=3,
            replica_trans_id='zed')
        self.assertGetDocConflicts(self.db, doc1.doc_id,
            [('alternate:2', doc22.get_json()),
             ('altalt:1', doc3.get_json()),
             (doc1.rev, simple_doc)])

    def test_put_doc_if_newer_save_conflict_was_deleted(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        self.db.delete_doc(doc1)
        doc2 = self.make_document(doc1.doc_id, 'alternate:1', nested_doc)
        self.db._put_doc_if_newer(
            doc2, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        self.assertTrue(doc2.has_conflicts)
        self.assertGetDoc(
            self.db, doc1.doc_id, 'alternate:1', nested_doc, True)
        self.assertGetDocConflicts(self.db, doc1.doc_id,
            [('alternate:1', nested_doc), (doc1.rev, None)])

    def test_put_doc_if_newer_propagates_full_resolution(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        doc2 = self.make_document(doc1.doc_id, 'alternate:1', nested_doc)
        self.db._put_doc_if_newer(
            doc2, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        resolved_vcr = vectorclock.VectorClockRev(doc1.rev)
        vcr_2 = vectorclock.VectorClockRev(doc2.rev)
        resolved_vcr.maximize(vcr_2)
        resolved_vcr.increment('alternate')
        doc_resolved = self.make_document(doc1.doc_id, resolved_vcr.as_str(),
                                '{"good": 1}')
        state, _ = self.db._put_doc_if_newer(
            doc_resolved, save_conflict=True, replica_uid='r', replica_gen=2,
            replica_trans_id='foo2')
        self.assertEqual('inserted', state)
        self.assertFalse(doc_resolved.has_conflicts)
        self.assertGetDocConflicts(self.db, doc1.doc_id, [])
        doc3 = self.db.get_doc(doc1.doc_id)
        self.assertFalse(doc3.has_conflicts)

    def test_put_doc_if_newer_propagates_partial_resolution(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        doc2 = self.make_document(doc1.doc_id, 'altalt:1', '{}')
        self.db._put_doc_if_newer(
            doc2, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        doc3 = self.make_document(doc1.doc_id, 'alternate:1', nested_doc)
        self.db._put_doc_if_newer(
            doc3, save_conflict=True, replica_uid='r', replica_gen=2,
            replica_trans_id='foo2')
        self.assertGetDocConflicts(self.db, doc1.doc_id,
            [('alternate:1', nested_doc), ('test:1', simple_doc),
             ('altalt:1', '{}')])
        resolved_vcr = vectorclock.VectorClockRev(doc1.rev)
        vcr_3 = vectorclock.VectorClockRev(doc3.rev)
        resolved_vcr.maximize(vcr_3)
        resolved_vcr.increment('alternate')
        doc_resolved = self.make_document(doc1.doc_id, resolved_vcr.as_str(),
                                          '{"good": 1}')
        state, _ = self.db._put_doc_if_newer(
            doc_resolved, save_conflict=True, replica_uid='r', replica_gen=3,
            replica_trans_id='foo3')
        self.assertEqual('inserted', state)
        self.assertTrue(doc_resolved.has_conflicts)
        doc4 = self.db.get_doc(doc1.doc_id)
        self.assertTrue(doc4.has_conflicts)
        self.assertGetDocConflicts(self.db, doc1.doc_id,
            [('alternate:2|test:1', '{"good": 1}'), ('altalt:1', '{}')])

    def test_put_doc_if_newer_replica_uid(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        self.db._set_replica_gen_and_trans_id('other', 1, 'T-id')
        doc2 = self.make_document(doc1.doc_id, doc1.rev + '|other:1',
                                  nested_doc)
        self.db._put_doc_if_newer(doc2, save_conflict=True,
                                  replica_uid='other', replica_gen=2,
                                  replica_trans_id='T-id2')
        # Conflict vs the current update
        doc2 = self.make_document(doc1.doc_id, doc1.rev + '|third:3',
                                  '{}')
        self.assertEqual('conflicted',
            self.db._put_doc_if_newer(doc2, save_conflict=True,
                replica_uid='other', replica_gen=3,
                replica_trans_id='T-id3')[0])
        self.assertEqual(
            (3, 'T-id3'), self.db._get_replica_gen_and_trans_id('other'))

    def test_put_doc_if_newer_autoresolve_2(self):
        # this is an ordering variant of _3, but that already works
        # adding the test explicitly to catch the regression easily
        doc_a1 = self.db.create_doc_from_json(simple_doc)
        doc_a2 = self.make_document(doc_a1.doc_id, 'test:2', "{}")
        doc_a1b1 = self.make_document(doc_a1.doc_id, 'test:1|other:1',
                                      '{"a":"42"}')
        doc_a3 = self.make_document(doc_a1.doc_id, 'test:2|other:1', "{}")
        state, _ = self.db._put_doc_if_newer(
            doc_a2, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        self.assertEqual(state, 'inserted')
        state, _ = self.db._put_doc_if_newer(
            doc_a1b1, save_conflict=True, replica_uid='r', replica_gen=2,
            replica_trans_id='foo2')
        self.assertEqual(state, 'conflicted')
        state, _ = self.db._put_doc_if_newer(
            doc_a3, save_conflict=True, replica_uid='r', replica_gen=3,
            replica_trans_id='foo3')
        self.assertEqual(state, 'inserted')
        self.assertFalse(self.db.get_doc(doc_a1.doc_id).has_conflicts)

    def test_put_doc_if_newer_autoresolve_3(self):
        doc_a1 = self.db.create_doc_from_json(simple_doc)
        doc_a1b1 = self.make_document(doc_a1.doc_id, 'test:1|other:1', "{}")
        doc_a2 = self.make_document(doc_a1.doc_id, 'test:2',  '{"a":"42"}')
        doc_a3 = self.make_document(doc_a1.doc_id, 'test:3', "{}")
        state, _ = self.db._put_doc_if_newer(
            doc_a1b1, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        self.assertEqual(state, 'inserted')
        state, _ = self.db._put_doc_if_newer(
            doc_a2, save_conflict=True, replica_uid='r', replica_gen=2,
            replica_trans_id='foo2')
        self.assertEqual(state, 'conflicted')
        state, _ = self.db._put_doc_if_newer(
            doc_a3, save_conflict=True, replica_uid='r', replica_gen=3,
            replica_trans_id='foo3')
        self.assertEqual(state, 'superseded')
        doc = self.db.get_doc(doc_a1.doc_id, True)
        self.assertFalse(doc.has_conflicts)
        rev = vectorclock.VectorClockRev(doc.rev)
        rev_a3 = vectorclock.VectorClockRev('test:3')
        rev_a1b1 = vectorclock.VectorClockRev('test:1|other:1')
        self.assertTrue(rev.is_newer(rev_a3))
        self.assertTrue('test:4' in doc.rev) # locally increased
        self.assertTrue(rev.is_newer(rev_a1b1))

    def test_put_doc_if_newer_autoresolve_4(self):
        doc_a1 = self.db.create_doc_from_json(simple_doc)
        doc_a1b1 = self.make_document(doc_a1.doc_id, 'test:1|other:1', None)
        doc_a2 = self.make_document(doc_a1.doc_id, 'test:2',  '{"a":"42"}')
        doc_a3 = self.make_document(doc_a1.doc_id, 'test:3', None)
        state, _ = self.db._put_doc_if_newer(
            doc_a1b1, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        self.assertEqual(state, 'inserted')
        state, _ = self.db._put_doc_if_newer(
            doc_a2, save_conflict=True, replica_uid='r', replica_gen=2,
            replica_trans_id='foo2')
        self.assertEqual(state, 'conflicted')
        state, _ = self.db._put_doc_if_newer(
            doc_a3, save_conflict=True, replica_uid='r', replica_gen=3,
            replica_trans_id='foo3')
        self.assertEqual(state, 'superseded')
        doc = self.db.get_doc(doc_a1.doc_id, True)
        self.assertFalse(doc.has_conflicts)
        rev = vectorclock.VectorClockRev(doc.rev)
        rev_a3 = vectorclock.VectorClockRev('test:3')
        rev_a1b1 = vectorclock.VectorClockRev('test:1|other:1')
        self.assertTrue(rev.is_newer(rev_a3))
        self.assertTrue('test:4' in doc.rev) # locally increased
        self.assertTrue(rev.is_newer(rev_a1b1))

    def test_put_refuses_to_update_conflicted(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        content2 = '{"key": "altval"}'
        doc2 = self.make_document(doc1.doc_id, 'altrev:1', content2)
        self.db._put_doc_if_newer(
            doc2, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        self.assertGetDoc(self.db, doc1.doc_id, doc2.rev, content2, True)
        content3 = '{"key": "local"}'
        doc2.set_json(content3)
        self.assertRaises(errors.ConflictedDoc, self.db.put_doc, doc2)

    def test_delete_refuses_for_conflicted(self):
        doc1 = self.db.create_doc_from_json(simple_doc)
        doc2 = self.make_document(doc1.doc_id, 'altrev:1', nested_doc)
        self.db._put_doc_if_newer(
            doc2, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        self.assertGetDoc(self.db, doc2.doc_id, doc2.rev, nested_doc, True)
        self.assertRaises(errors.ConflictedDoc, self.db.delete_doc, doc2)


class DatabaseIndexTests(tests.DatabaseBaseTests):

    scenarios = tests.LOCAL_DATABASES_SCENARIOS #+ tests.C_DATABASE_SCENARIOS

    def assertParseError(self, definition):
        self.db.create_doc_from_json(nested_doc)
        self.assertRaises(
            errors.IndexDefinitionParseError, self.db.create_index, 'idx',
            definition)

    def assertIndexCreatable(self, definition):
        name = "idx"
        self.db.create_doc_from_json(nested_doc)
        self.db.create_index(name, definition)
        self.assertEqual(
            [(name, [definition])], self.db.list_indexes())

    def test_create_index(self):
        self.db.create_index('test-idx', 'name')
        self.assertEqual([('test-idx', ['name'])],
                         self.db.list_indexes())

    def test_create_index_on_non_ascii_field_name(self):
        doc = self.db.create_doc_from_json(json.dumps({u'\xe5': 'value'}))
        self.db.create_index('test-idx', u'\xe5')
        self.assertEqual([doc], self.db.get_from_index('test-idx', 'value'))

    def test_list_indexes_with_non_ascii_field_names(self):
        self.db.create_index('test-idx', u'\xe5')
        self.assertEqual(
            [('test-idx', [u'\xe5'])], self.db.list_indexes())

    def test_create_index_evaluates_it(self):
        doc = self.db.create_doc_from_json(simple_doc)
        self.db.create_index('test-idx', 'key')
        self.assertEqual([doc], self.db.get_from_index('test-idx', 'value'))

    def test_wildcard_matches_unicode_value(self):
        doc = self.db.create_doc_from_json(json.dumps({"key": u"valu\xe5"}))
        self.db.create_index('test-idx', 'key')
        self.assertEqual([doc], self.db.get_from_index('test-idx', '*'))

    def test_retrieve_unicode_value_from_index(self):
        doc = self.db.create_doc_from_json(json.dumps({"key": u"valu\xe5"}))
        self.db.create_index('test-idx', 'key')
        self.assertEqual(
            [doc], self.db.get_from_index('test-idx', u"valu\xe5"))

    def test_create_index_fails_if_name_taken(self):
        self.db.create_index('test-idx', 'key')
        self.assertRaises(errors.IndexNameTakenError,
                          self.db.create_index,
                          'test-idx', 'stuff')

    def test_create_index_does_not_fail_if_name_taken_with_same_index(self):
        self.db.create_index('test-idx', 'key')
        self.db.create_index('test-idx', 'key')
        self.assertEqual([('test-idx', ['key'])], self.db.list_indexes())

    def test_create_index_does_not_duplicate_indexed_fields(self):
        self.db.create_doc_from_json(simple_doc)
        self.db.create_index('test-idx', 'key')
        self.db.delete_index('test-idx')
        self.db.create_index('test-idx', 'key')
        self.assertEqual(1, len(self.db.get_from_index('test-idx', 'value')))

    def test_delete_index_does_not_remove_fields_from_other_indexes(self):
        self.db.create_doc_from_json(simple_doc)
        self.db.create_index('test-idx', 'key')
        self.db.create_index('test-idx2', 'key')
        self.db.delete_index('test-idx')
        self.assertEqual(1, len(self.db.get_from_index('test-idx2', 'value')))

    def test_create_index_after_deleting_document(self):
        doc = self.db.create_doc_from_json(simple_doc)
        doc2 = self.db.create_doc_from_json(simple_doc)
        self.db.delete_doc(doc2)
        self.db.create_index('test-idx', 'key')
        self.assertEqual([doc], self.db.get_from_index('test-idx', 'value'))

    def test_delete_index(self):
        self.db.create_index('test-idx', 'key')
        self.assertEqual([('test-idx', ['key'])], self.db.list_indexes())
        self.db.delete_index('test-idx')
        self.assertEqual([], self.db.list_indexes())

    def test_create_adds_to_index(self):
        self.db.create_index('test-idx', 'key')
        doc = self.db.create_doc_from_json(simple_doc)
        self.assertEqual([doc], self.db.get_from_index('test-idx', 'value'))

    def test_get_from_index_unmatched(self):
        self.db.create_doc_from_json(simple_doc)
        self.db.create_index('test-idx', 'key')
        self.assertEqual([], self.db.get_from_index('test-idx', 'novalue'))

    def test_create_index_multiple_exact_matches(self):
        doc = self.db.create_doc_from_json(simple_doc)
        doc2 = self.db.create_doc_from_json(simple_doc)
        self.db.create_index('test-idx', 'key')
        self.assertEqual(
            sorted([doc, doc2]),
            sorted(self.db.get_from_index('test-idx', 'value')))

    def test_get_from_index(self):
        doc = self.db.create_doc_from_json(simple_doc)
        self.db.create_index('test-idx', 'key')
        self.assertEqual([doc], self.db.get_from_index('test-idx', 'value'))

    def test_get_from_index_multi(self):
        content = '{"key": "value", "key2": "value2"}'
        doc = self.db.create_doc_from_json(content)
        self.db.create_index('test-idx', 'key', 'key2')
        self.assertEqual(
            [doc], self.db.get_from_index('test-idx', 'value', 'value2'))

    def test_get_from_index_multi_list(self):
        doc = self.db.create_doc_from_json(
            '{"key": "value", "key2": ["value2-1", "value2-2", "value2-3"]}')
        self.db.create_index('test-idx', 'key', 'key2')
        self.assertEqual(
            [doc], self.db.get_from_index('test-idx', 'value', 'value2-1'))
        self.assertEqual(
            [doc], self.db.get_from_index('test-idx', 'value', 'value2-2'))
        self.assertEqual(
            [doc], self.db.get_from_index('test-idx', 'value', 'value2-3'))
        self.assertEqual(
            [('value', 'value2-1'), ('value', 'value2-2'),
             ('value', 'value2-3')],
            sorted(self.db.get_index_keys('test-idx')))

    def test_get_from_index_sees_conflicts(self):
        doc = self.db.create_doc_from_json(simple_doc)
        self.db.create_index('test-idx', 'key', 'key2')
        alt_doc = self.make_document(
            doc.doc_id, 'alternate:1',
            '{"key": "value", "key2": ["value2-1", "value2-2", "value2-3"]}')
        self.db._put_doc_if_newer(
            alt_doc, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        docs = self.db.get_from_index('test-idx', 'value', 'value2-1')
        self.assertTrue(docs[0].has_conflicts)

    def test_get_index_keys_multi_list_list(self):
        self.db.create_doc_from_json(
            '{"key": "value1-1 value1-2 value1-3", '
            '"key2": ["value2-1", "value2-2", "value2-3"]}')
        self.db.create_index('test-idx', 'split_words(key)', 'key2')
        self.assertEqual(
            [(u'value1-1', u'value2-1'), (u'value1-1', u'value2-2'),
             (u'value1-1', u'value2-3'), (u'value1-2', u'value2-1'),
             (u'value1-2', u'value2-2'), (u'value1-2', u'value2-3'),
             (u'value1-3', u'value2-1'), (u'value1-3', u'value2-2'),
             (u'value1-3', u'value2-3')],
            sorted(self.db.get_index_keys('test-idx')))

    def test_get_from_index_multi_ordered(self):
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
            self.db.get_from_index('test-idx', 'v*', '*'))

    def test_get_range_from_index_start_end(self):
        doc1 = self.db.create_doc_from_json('{"key": "value3"}')
        doc2 = self.db.create_doc_from_json('{"key": "value2"}')
        self.db.create_doc_from_json('{"key": "value4"}')
        self.db.create_doc_from_json('{"key": "value1"}')
        self.db.create_index('test-idx', 'key')
        self.assertEqual(
            [doc2, doc1],
            self.db.get_range_from_index('test-idx', 'value2', 'value3'))

    def test_get_range_from_index_start(self):
        doc1 = self.db.create_doc_from_json('{"key": "value3"}')
        doc2 = self.db.create_doc_from_json('{"key": "value2"}')
        doc3 = self.db.create_doc_from_json('{"key": "value4"}')
        self.db.create_doc_from_json('{"key": "value1"}')
        self.db.create_index('test-idx', 'key')
        self.assertEqual(
            [doc2, doc1, doc3],
            self.db.get_range_from_index('test-idx', 'value2'))

    def test_get_range_from_index_sees_conflicts(self):
        doc = self.db.create_doc_from_json(simple_doc)
        self.db.create_index('test-idx', 'key')
        alt_doc = self.make_document(
            doc.doc_id, 'alternate:1', '{"key": "valuedepalue"}')
        self.db._put_doc_if_newer(
            alt_doc, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        docs = self.db.get_range_from_index('test-idx', 'a')
        self.assertTrue(docs[0].has_conflicts)

    def test_get_range_from_index_end(self):
        self.db.create_doc_from_json('{"key": "value3"}')
        doc2 = self.db.create_doc_from_json('{"key": "value2"}')
        self.db.create_doc_from_json('{"key": "value4"}')
        doc4 = self.db.create_doc_from_json('{"key": "value1"}')
        self.db.create_index('test-idx', 'key')
        self.assertEqual(
            [doc4, doc2],
            self.db.get_range_from_index('test-idx', None, 'value2'))

    def test_get_wildcard_range_from_index_start(self):
        doc1 = self.db.create_doc_from_json('{"key": "value4"}')
        doc2 = self.db.create_doc_from_json('{"key": "value23"}')
        doc3 = self.db.create_doc_from_json('{"key": "value2"}')
        doc4 = self.db.create_doc_from_json('{"key": "value22"}')
        self.db.create_doc_from_json('{"key": "value1"}')
        self.db.create_index('test-idx', 'key')
        self.assertEqual(
            [doc3, doc4, doc2, doc1],
            self.db.get_range_from_index('test-idx', 'value2*'))

    def test_get_wildcard_range_from_index_end(self):
        self.db.create_doc_from_json('{"key": "value4"}')
        doc2 = self.db.create_doc_from_json('{"key": "value23"}')
        doc3 = self.db.create_doc_from_json('{"key": "value2"}')
        doc4 = self.db.create_doc_from_json('{"key": "value22"}')
        doc5 = self.db.create_doc_from_json('{"key": "value1"}')
        self.db.create_index('test-idx', 'key')
        self.assertEqual(
            [doc5, doc3, doc4, doc2],
            self.db.get_range_from_index('test-idx', None, 'value2*'))

    def test_get_wildcard_range_from_index_start_end(self):
        self.db.create_doc_from_json('{"key": "a"}')
        self.db.create_doc_from_json('{"key": "boo3"}')
        doc3 = self.db.create_doc_from_json('{"key": "catalyst"}')
        doc4 = self.db.create_doc_from_json('{"key": "whaever"}')
        self.db.create_doc_from_json('{"key": "zerg"}')
        self.db.create_index('test-idx', 'key')
        self.assertEqual(
            [doc3, doc4],
            self.db.get_range_from_index('test-idx', 'cat*', 'zap*'))

    def test_get_range_from_index_multi_column_start_end(self):
        self.db.create_doc_from_json('{"key": "value3", "key2": "value4"}')
        doc2 = self.db.create_doc_from_json(
            '{"key": "value2", "key2": "value3"}')
        doc3 = self.db.create_doc_from_json(
            '{"key": "value2", "key2": "value2"}')
        self.db.create_doc_from_json('{"key": "value1", "key2": "value1"}')
        self.db.create_index('test-idx', 'key', 'key2')
        self.assertEqual(
            [doc3, doc2],
            self.db.get_range_from_index(
                'test-idx', ('value2', 'value2'), ('value2', 'value3')))

    def test_get_range_from_index_multi_column_start(self):
        doc1 = self.db.create_doc_from_json(
            '{"key": "value3", "key2": "value4"}')
        doc2 = self.db.create_doc_from_json(
            '{"key": "value2", "key2": "value3"}')
        self.db.create_doc_from_json('{"key": "value2", "key2": "value2"}')
        self.db.create_doc_from_json('{"key": "value1", "key2": "value1"}')
        self.db.create_index('test-idx', 'key', 'key2')
        self.assertEqual(
            [doc2, doc1],
            self.db.get_range_from_index('test-idx', ('value2', 'value3')))

    def test_get_range_from_index_multi_column_end(self):
        self.db.create_doc_from_json('{"key": "value3", "key2": "value4"}')
        doc2 = self.db.create_doc_from_json(
            '{"key": "value2", "key2": "value3"}')
        doc3 = self.db.create_doc_from_json(
            '{"key": "value2", "key2": "value2"}')
        doc4 = self.db.create_doc_from_json(
            '{"key": "value1", "key2": "value1"}')
        self.db.create_index('test-idx', 'key', 'key2')
        self.assertEqual(
            [doc4, doc3, doc2],
            self.db.get_range_from_index(
                'test-idx', None, ('value2', 'value3')))

    def test_get_wildcard_range_from_index_multi_column_start(self):
        doc1 = self.db.create_doc_from_json(
            '{"key": "value3", "key2": "value4"}')
        doc2 = self.db.create_doc_from_json(
            '{"key": "value2", "key2": "value23"}')
        doc3 = self.db.create_doc_from_json(
            '{"key": "value2", "key2": "value2"}')
        self.db.create_doc_from_json('{"key": "value1", "key2": "value1"}')
        self.db.create_index('test-idx', 'key', 'key2')
        self.assertEqual(
            [doc3, doc2, doc1],
            self.db.get_range_from_index('test-idx', ('value2', 'value2*')))

    def test_get_wildcard_range_from_index_multi_column_end(self):
        self.db.create_doc_from_json('{"key": "value3", "key2": "value4"}')
        doc2 = self.db.create_doc_from_json(
            '{"key": "value2", "key2": "value23"}')
        doc3 = self.db.create_doc_from_json(
            '{"key": "value2", "key2": "value2"}')
        doc4 = self.db.create_doc_from_json(
            '{"key": "value1", "key2": "value1"}')
        self.db.create_index('test-idx', 'key', 'key2')
        self.assertEqual(
            [doc4, doc3, doc2],
            self.db.get_range_from_index(
                'test-idx', None, ('value2', 'value2*')))

    def test_get_glob_range_from_index_multi_column_start(self):
        doc1 = self.db.create_doc_from_json(
            '{"key": "value3", "key2": "value4"}')
        doc2 = self.db.create_doc_from_json(
            '{"key": "value2", "key2": "value23"}')
        self.db.create_doc_from_json('{"key": "value1", "key2": "value2"}')
        self.db.create_doc_from_json('{"key": "value1", "key2": "value1"}')
        self.db.create_index('test-idx', 'key', 'key2')
        self.assertEqual(
            [doc2, doc1],
            self.db.get_range_from_index('test-idx', ('value2', '*')))

    def test_get_glob_range_from_index_multi_column_end(self):
        self.db.create_doc_from_json('{"key": "value3", "key2": "value4"}')
        doc2 = self.db.create_doc_from_json(
            '{"key": "value2", "key2": "value23"}')
        doc3 = self.db.create_doc_from_json(
            '{"key": "value1", "key2": "value2"}')
        doc4 = self.db.create_doc_from_json(
            '{"key": "value1", "key2": "value1"}')
        self.db.create_index('test-idx', 'key', 'key2')
        self.assertEqual(
            [doc4, doc3, doc2],
            self.db.get_range_from_index('test-idx', None, ('value2', '*')))

    def test_get_range_from_index_illegal_wildcard_order(self):
        self.db.create_index('test-idx', 'k1', 'k2')
        self.assertRaises(
            errors.InvalidGlobbing,
            self.db.get_range_from_index, 'test-idx', ('*', 'v2'))

    def test_get_range_from_index_illegal_glob_after_wildcard(self):
        self.db.create_index('test-idx', 'k1', 'k2')
        self.assertRaises(
            errors.InvalidGlobbing,
            self.db.get_range_from_index, 'test-idx', ('*', 'v*'))

    def test_get_range_from_index_illegal_wildcard_order_end(self):
        self.db.create_index('test-idx', 'k1', 'k2')
        self.assertRaises(
            errors.InvalidGlobbing,
            self.db.get_range_from_index, 'test-idx', None, ('*', 'v2'))

    def test_get_range_from_index_illegal_glob_after_wildcard_end(self):
        self.db.create_index('test-idx', 'k1', 'k2')
        self.assertRaises(
            errors.InvalidGlobbing,
            self.db.get_range_from_index, 'test-idx', None, ('*', 'v*'))

    def test_get_from_index_fails_if_no_index(self):
        self.assertRaises(
            errors.IndexDoesNotExist, self.db.get_from_index, 'foo')

    def test_get_index_keys_fails_if_no_index(self):
        self.assertRaises(errors.IndexDoesNotExist,
                          self.db.get_index_keys,
                          'foo')

    def test_get_index_keys_works_if_no_docs(self):
        self.db.create_index('test-idx', 'key')
        self.assertEqual([], self.db.get_index_keys('test-idx'))

    def test_put_updates_index(self):
        doc = self.db.create_doc_from_json(simple_doc)
        self.db.create_index('test-idx', 'key')
        new_content = '{"key": "altval"}'
        doc.set_json(new_content)
        self.db.put_doc(doc)
        self.assertEqual([], self.db.get_from_index('test-idx', 'value'))
        self.assertEqual([doc], self.db.get_from_index('test-idx', 'altval'))

    def test_delete_updates_index(self):
        doc = self.db.create_doc_from_json(simple_doc)
        doc2 = self.db.create_doc_from_json(simple_doc)
        self.db.create_index('test-idx', 'key')
        self.assertEqual(
            sorted([doc, doc2]),
            sorted(self.db.get_from_index('test-idx', 'value')))
        self.db.delete_doc(doc)
        self.assertEqual([doc2], self.db.get_from_index('test-idx', 'value'))

    def test_get_from_index_illegal_number_of_entries(self):
        self.db.create_index('test-idx', 'k1', 'k2')
        self.assertRaises(
            errors.InvalidValueForIndex, self.db.get_from_index, 'test-idx')
        self.assertRaises(
            errors.InvalidValueForIndex,
            self.db.get_from_index, 'test-idx', 'v1')
        self.assertRaises(
            errors.InvalidValueForIndex,
            self.db.get_from_index, 'test-idx', 'v1', 'v2', 'v3')

    def test_get_from_index_illegal_wildcard_order(self):
        self.db.create_index('test-idx', 'k1', 'k2')
        self.assertRaises(
            errors.InvalidGlobbing,
            self.db.get_from_index, 'test-idx', '*', 'v2')

    def test_get_from_index_illegal_glob_after_wildcard(self):
        self.db.create_index('test-idx', 'k1', 'k2')
        self.assertRaises(
            errors.InvalidGlobbing,
            self.db.get_from_index, 'test-idx', '*', 'v*')

    def test_get_all_from_index(self):
        self.db.create_index('test-idx', 'key')
        doc1 = self.db.create_doc_from_json(simple_doc)
        doc2 = self.db.create_doc_from_json(nested_doc)
        # This one should not be in the index
        self.db.create_doc_from_json('{"no": "key"}')
        diff_value_doc = '{"key": "diff value"}'
        doc4 = self.db.create_doc_from_json(diff_value_doc)
        # This is essentially a 'prefix' match, but we match every entry.
        self.assertEqual(
            sorted([doc1, doc2, doc4]),
            sorted(self.db.get_from_index('test-idx', '*')))

    def test_get_all_from_index_ordered(self):
        self.db.create_index('test-idx', 'key')
        doc1 = self.db.create_doc_from_json('{"key": "value x"}')
        doc2 = self.db.create_doc_from_json('{"key": "value b"}')
        doc3 = self.db.create_doc_from_json('{"key": "value a"}')
        doc4 = self.db.create_doc_from_json('{"key": "value m"}')
        # This is essentially a 'prefix' match, but we match every entry.
        self.assertEqual(
            [doc3, doc2, doc4, doc1], self.db.get_from_index('test-idx', '*'))

    def test_put_updates_when_adding_key(self):
        doc = self.db.create_doc_from_json("{}")
        self.db.create_index('test-idx', 'key')
        self.assertEqual([], self.db.get_from_index('test-idx', '*'))
        doc.set_json(simple_doc)
        self.db.put_doc(doc)
        self.assertEqual([doc], self.db.get_from_index('test-idx', '*'))

    def test_get_from_index_empty_string(self):
        self.db.create_index('test-idx', 'key')
        doc1 = self.db.create_doc_from_json(simple_doc)
        content2 = '{"key": ""}'
        doc2 = self.db.create_doc_from_json(content2)
        self.assertEqual([doc2], self.db.get_from_index('test-idx', ''))
        # Empty string matches the wildcard.
        self.assertEqual(
            sorted([doc1, doc2]),
            sorted(self.db.get_from_index('test-idx', '*')))

    def test_get_from_index_not_null(self):
        self.db.create_index('test-idx', 'key')
        doc1 = self.db.create_doc_from_json(simple_doc)
        self.db.create_doc_from_json('{"key": null}')
        self.assertEqual([doc1], self.db.get_from_index('test-idx', '*'))

    def test_get_partial_from_index(self):
        content1 = '{"k1": "v1", "k2": "v2"}'
        content2 = '{"k1": "v1", "k2": "x2"}'
        content3 = '{"k1": "v1", "k2": "y2"}'
        # doc4 has a different k1 value, so it doesn't match the prefix.
        content4 = '{"k1": "NN", "k2": "v2"}'
        doc1 = self.db.create_doc_from_json(content1)
        doc2 = self.db.create_doc_from_json(content2)
        doc3 = self.db.create_doc_from_json(content3)
        self.db.create_doc_from_json(content4)
        self.db.create_index('test-idx', 'k1', 'k2')
        self.assertEqual(
            sorted([doc1, doc2, doc3]),
            sorted(self.db.get_from_index('test-idx', "v1", "*")))

    def test_get_glob_match(self):
        # Note: the exact glob syntax is probably subject to change
        content1 = '{"k1": "v1", "k2": "v1"}'
        content2 = '{"k1": "v1", "k2": "v2"}'
        content3 = '{"k1": "v1", "k2": "v3"}'
        # doc4 has a different k2 prefix value, so it doesn't match
        content4 = '{"k1": "v1", "k2": "ZZ"}'
        self.db.create_index('test-idx', 'k1', 'k2')
        doc1 = self.db.create_doc_from_json(content1)
        doc2 = self.db.create_doc_from_json(content2)
        doc3 = self.db.create_doc_from_json(content3)
        self.db.create_doc_from_json(content4)
        self.assertEqual(
            sorted([doc1, doc2, doc3]),
            sorted(self.db.get_from_index('test-idx', "v1", "v*")))

    def test_nested_index(self):
        doc = self.db.create_doc_from_json(nested_doc)
        self.db.create_index('test-idx', 'sub.doc')
        self.assertEqual(
            [doc], self.db.get_from_index('test-idx', 'underneath'))
        doc2 = self.db.create_doc_from_json(nested_doc)
        self.assertEqual(
            sorted([doc, doc2]),
            sorted(self.db.get_from_index('test-idx', 'underneath')))

    def test_nested_nonexistent(self):
        self.db.create_doc_from_json(nested_doc)
        # sub exists, but sub.foo does not:
        self.db.create_index('test-idx', 'sub.foo')
        self.assertEqual([], self.db.get_from_index('test-idx', '*'))

    def test_nested_nonexistent2(self):
        self.db.create_doc_from_json(nested_doc)
        self.db.create_index('test-idx', 'sub.foo.bar.baz.qux.fnord')
        self.assertEqual([], self.db.get_from_index('test-idx', '*'))

    def test_nested_traverses_lists(self):
        # subpath finds dicts in list
        doc = self.db.create_doc_from_json(
            '{"foo": [{"zap": "bar"}, {"zap": "baz"}]}')
        # subpath only finds dicts in list
        self.db.create_doc_from_json('{"foo": ["zap", "baz"]}')
        self.db.create_index('test-idx', 'foo.zap')
        self.assertEqual([doc], self.db.get_from_index('test-idx', 'bar'))
        self.assertEqual([doc], self.db.get_from_index('test-idx', 'baz'))

    def test_nested_list_traversal(self):
        # subpath finds dicts in list
        doc = self.db.create_doc_from_json(
            '{"foo": [{"zap": [{"qux": "fnord"}, {"qux": "zombo"}]},'
            '{"zap": "baz"}]}')
        # subpath only finds dicts in list
        self.db.create_index('test-idx', 'foo.zap.qux')
        self.assertEqual([doc], self.db.get_from_index('test-idx', 'fnord'))
        self.assertEqual([doc], self.db.get_from_index('test-idx', 'zombo'))

    def test_index_list1(self):
        self.db.create_index("index", "name")
        content = '{"name": ["foo", "bar"]}'
        doc = self.db.create_doc_from_json(content)
        rows = self.db.get_from_index("index", "bar")
        self.assertEqual([doc], rows)

    def test_index_list2(self):
        self.db.create_index("index", "name")
        content = '{"name": ["foo", "bar"]}'
        doc = self.db.create_doc_from_json(content)
        rows = self.db.get_from_index("index", "foo")
        self.assertEqual([doc], rows)

    def test_get_from_index_case_sensitive(self):
        self.db.create_index('test-idx', 'key')
        doc1 = self.db.create_doc_from_json(simple_doc)
        self.assertEqual([], self.db.get_from_index('test-idx', 'V*'))
        self.assertEqual([doc1], self.db.get_from_index('test-idx', 'v*'))

    def test_get_from_index_illegal_glob_before_value(self):
        self.db.create_index('test-idx', 'k1', 'k2')
        self.assertRaises(
            errors.InvalidGlobbing,
            self.db.get_from_index, 'test-idx', 'v*', 'v2')

    def test_get_from_index_illegal_glob_after_glob(self):
        self.db.create_index('test-idx', 'k1', 'k2')
        self.assertRaises(
            errors.InvalidGlobbing,
            self.db.get_from_index, 'test-idx', 'v*', 'v*')

    def test_get_from_index_with_sql_wildcards(self):
        self.db.create_index('test-idx', 'key')
        content1 = '{"key": "va%lue"}'
        content2 = '{"key": "value"}'
        content3 = '{"key": "va_lue"}'
        doc1 = self.db.create_doc_from_json(content1)
        self.db.create_doc_from_json(content2)
        doc3 = self.db.create_doc_from_json(content3)
        # The '%' in the search should be treated literally, not as a sql
        # globbing character.
        self.assertEqual([doc1], self.db.get_from_index('test-idx', 'va%*'))
        # Same for '_'
        self.assertEqual([doc3], self.db.get_from_index('test-idx', 'va_*'))

    def test_get_from_index_with_lower(self):
        self.db.create_index("index", "lower(name)")
        content = '{"name": "Foo"}'
        doc = self.db.create_doc_from_json(content)
        rows = self.db.get_from_index("index", "foo")
        self.assertEqual([doc], rows)

    def test_get_from_index_with_lower_matches_same_case(self):
        self.db.create_index("index", "lower(name)")
        content = '{"name": "foo"}'
        doc = self.db.create_doc_from_json(content)
        rows = self.db.get_from_index("index", "foo")
        self.assertEqual([doc], rows)

    def test_index_lower_doesnt_match_different_case(self):
        self.db.create_index("index", "lower(name)")
        content = '{"name": "Foo"}'
        self.db.create_doc_from_json(content)
        rows = self.db.get_from_index("index", "Foo")
        self.assertEqual([], rows)

    def test_index_lower_doesnt_match_other_index(self):
        self.db.create_index("index", "lower(name)")
        self.db.create_index("other_index", "name")
        content = '{"name": "Foo"}'
        self.db.create_doc_from_json(content)
        rows = self.db.get_from_index("index", "Foo")
        self.assertEqual(0, len(rows))

    def test_index_split_words_match_first(self):
        self.db.create_index("index", "split_words(name)")
        content = '{"name": "foo bar"}'
        doc = self.db.create_doc_from_json(content)
        rows = self.db.get_from_index("index", "foo")
        self.assertEqual([doc], rows)

    def test_index_split_words_match_second(self):
        self.db.create_index("index", "split_words(name)")
        content = '{"name": "foo bar"}'
        doc = self.db.create_doc_from_json(content)
        rows = self.db.get_from_index("index", "bar")
        self.assertEqual([doc], rows)

    def test_index_split_words_match_both(self):
        self.db.create_index("index", "split_words(name)")
        content = '{"name": "foo foo"}'
        doc = self.db.create_doc_from_json(content)
        rows = self.db.get_from_index("index", "foo")
        self.assertEqual([doc], rows)

    def test_index_split_words_double_space(self):
        self.db.create_index("index", "split_words(name)")
        content = '{"name": "foo  bar"}'
        doc = self.db.create_doc_from_json(content)
        rows = self.db.get_from_index("index", "bar")
        self.assertEqual([doc], rows)

    def test_index_split_words_leading_space(self):
        self.db.create_index("index", "split_words(name)")
        content = '{"name": " foo bar"}'
        doc = self.db.create_doc_from_json(content)
        rows = self.db.get_from_index("index", "foo")
        self.assertEqual([doc], rows)

    def test_index_split_words_trailing_space(self):
        self.db.create_index("index", "split_words(name)")
        content = '{"name": "foo bar "}'
        doc = self.db.create_doc_from_json(content)
        rows = self.db.get_from_index("index", "bar")
        self.assertEqual([doc], rows)

    def test_get_from_index_with_number(self):
        self.db.create_index("index", "number(foo, 5)")
        content = '{"foo": 12}'
        doc = self.db.create_doc_from_json(content)
        rows = self.db.get_from_index("index", "00012")
        self.assertEqual([doc], rows)

    def test_get_from_index_with_number_bigger_than_padding(self):
        self.db.create_index("index", "number(foo, 5)")
        content = '{"foo": 123456}'
        doc = self.db.create_doc_from_json(content)
        rows = self.db.get_from_index("index", "123456")
        self.assertEqual([doc], rows)

    def test_number_mapping_ignores_non_numbers(self):
        self.db.create_index("index", "number(foo, 5)")
        content = '{"foo": 56}'
        doc1 = self.db.create_doc_from_json(content)
        content = '{"foo": "this is not a maigret painting"}'
        self.db.create_doc_from_json(content)
        rows = self.db.get_from_index("index", "*")
        self.assertEqual([doc1], rows)

    def test_get_from_index_with_bool(self):
        self.db.create_index("index", "bool(foo)")
        content = '{"foo": true}'
        doc = self.db.create_doc_from_json(content)
        rows = self.db.get_from_index("index", "1")
        self.assertEqual([doc], rows)

    def test_get_from_index_with_bool_false(self):
        self.db.create_index("index", "bool(foo)")
        content = '{"foo": false}'
        doc = self.db.create_doc_from_json(content)
        rows = self.db.get_from_index("index", "0")
        self.assertEqual([doc], rows)

    def test_get_from_index_with_non_bool(self):
        self.db.create_index("index", "bool(foo)")
        content = '{"foo": 42}'
        self.db.create_doc_from_json(content)
        rows = self.db.get_from_index("index", "*")
        self.assertEqual([], rows)

    def test_get_from_index_with_combine(self):
        self.db.create_index("index", "combine(foo, bar)")
        content = '{"foo": "value1", "bar": "value2"}'
        doc = self.db.create_doc_from_json(content)
        rows = self.db.get_from_index("index", "value1")
        self.assertEqual([doc], rows)
        rows = self.db.get_from_index("index", "value2")
        self.assertEqual([doc], rows)

    def test_get_complex_combine(self):
        self.db.create_index(
            "index", "combine(number(foo, 5), lower(bar), split_words(baz))")
        content = '{"foo": 12, "bar": "ALLCAPS", "baz": "qux nox"}'
        doc = self.db.create_doc_from_json(content)
        content = '{"foo": "not a number", "bar": "something"}'
        doc2 = self.db.create_doc_from_json(content)
        rows = self.db.get_from_index("index", "00012")
        self.assertEqual([doc], rows)
        rows = self.db.get_from_index("index", "allcaps")
        self.assertEqual([doc], rows)
        rows = self.db.get_from_index("index", "nox")
        self.assertEqual([doc], rows)
        rows = self.db.get_from_index("index", "something")
        self.assertEqual([doc2], rows)

    def test_get_index_keys_from_index(self):
        self.db.create_index('test-idx', 'key')
        content1 = '{"key": "value1"}'
        content2 = '{"key": "value2"}'
        content3 = '{"key": "value2"}'
        self.db.create_doc_from_json(content1)
        self.db.create_doc_from_json(content2)
        self.db.create_doc_from_json(content3)
        self.assertEqual(
            [('value1',), ('value2',)],
            sorted(self.db.get_index_keys('test-idx')))

    def test_get_index_keys_from_multicolumn_index(self):
        self.db.create_index('test-idx', 'key1', 'key2')
        content1 = '{"key1": "value1", "key2": "val2-1"}'
        content2 = '{"key1": "value2", "key2": "val2-2"}'
        content3 = '{"key1": "value2", "key2": "val2-2"}'
        content4 = '{"key1": "value2", "key2": "val3"}'
        self.db.create_doc_from_json(content1)
        self.db.create_doc_from_json(content2)
        self.db.create_doc_from_json(content3)
        self.db.create_doc_from_json(content4)
        self.assertEqual([
            ('value1', 'val2-1'),
            ('value2', 'val2-2'),
            ('value2', 'val3')],
            sorted(self.db.get_index_keys('test-idx')))

    def test_empty_expr(self):
        self.assertParseError('')

    def test_nested_unknown_operation(self):
        self.assertParseError('unknown_operation(field1)')

    def test_parse_missing_close_paren(self):
        self.assertParseError("lower(a")

    def test_parse_trailing_close_paren(self):
        self.assertParseError("lower(ab))")

    def test_parse_trailing_chars(self):
        self.assertParseError("lower(ab)adsf")

    def test_parse_empty_op(self):
        self.assertParseError("(ab)")

    def test_parse_top_level_commas(self):
        self.assertParseError("a, b")

    def test_invalid_field_name(self):
        self.assertParseError("a.")

    def test_invalid_inner_field_name(self):
        self.assertParseError("lower(a.)")

    def test_gobbledigook(self):
        self.assertParseError("(@#@cc   @#!*DFJSXV(()jccd")

    def test_leading_space(self):
        self.assertIndexCreatable("  lower(a)")

    def test_trailing_space(self):
        self.assertIndexCreatable("lower(a)  ")

    def test_spaces_before_open_paren(self):
        self.assertIndexCreatable("lower  (a)")

    def test_spaces_after_open_paren(self):
        self.assertIndexCreatable("lower(  a)")

    def test_spaces_before_close_paren(self):
        self.assertIndexCreatable("lower(a  )")

    def test_spaces_before_comma(self):
        self.assertIndexCreatable("combine(a  , b  , c)")

    def test_spaces_after_comma(self):
        self.assertIndexCreatable("combine(a,  b,  c)")

    def test_all_together_now(self):
        self.assertParseError('    (a) ')

    def test_all_together_now2(self):
        self.assertParseError('combine(lower(x)x,foo)')


class PythonBackendTests(tests.DatabaseBaseTests):

    def setUp(self):
        super(PythonBackendTests, self).setUp()
        self.simple_doc = json.loads(simple_doc)

    def test_create_doc_with_factory(self):
        self.db.set_document_factory(TestAlternativeDocument)
        doc = self.db.create_doc(self.simple_doc, doc_id='my_doc_id')
        self.assertTrue(isinstance(doc, TestAlternativeDocument))

    def test_get_doc_after_put_with_factory(self):
        doc = self.db.create_doc(self.simple_doc, doc_id='my_doc_id')
        self.db.set_document_factory(TestAlternativeDocument)
        result = self.db.get_doc('my_doc_id')
        self.assertTrue(isinstance(result, TestAlternativeDocument))
        self.assertEqual(doc.doc_id, result.doc_id)
        self.assertEqual(doc.rev, result.rev)
        self.assertEqual(doc.get_json(), result.get_json())
        self.assertEqual(False, result.has_conflicts)

    def test_get_doc_nonexisting_with_factory(self):
        self.db.set_document_factory(TestAlternativeDocument)
        self.assertIs(None, self.db.get_doc('non-existing'))

    def test_get_all_docs_with_factory(self):
        self.db.set_document_factory(TestAlternativeDocument)
        self.db.create_doc(self.simple_doc)
        self.assertTrue(isinstance(
            list(self.db.get_all_docs()[1])[0], TestAlternativeDocument))

    def test_get_docs_conflicted_with_factory(self):
        self.db.set_document_factory(TestAlternativeDocument)
        doc1 = self.db.create_doc(self.simple_doc)
        doc2 = self.make_document(doc1.doc_id, 'alternate:1', nested_doc)
        self.db._put_doc_if_newer(
            doc2, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        self.assertTrue(
            isinstance(
                list(self.db.get_docs([doc1.doc_id]))[0],
                TestAlternativeDocument))

    def test_get_from_index_with_factory(self):
        self.db.set_document_factory(TestAlternativeDocument)
        self.db.create_doc(self.simple_doc)
        self.db.create_index('test-idx', 'key')
        self.assertTrue(
            isinstance(
                self.db.get_from_index('test-idx', 'value')[0],
                TestAlternativeDocument))

    def test_sync_exchange_updates_indexes(self):
        doc = self.db.create_doc(self.simple_doc)
        self.db.create_index('test-idx', 'key')
        new_content = '{"key": "altval"}'
        other_rev = 'test:1|z:2'
        st = self.db.get_sync_target()

        def ignore(doc_id, doc_rev, doc):
            pass

        doc_other = self.make_document(doc.doc_id, other_rev, new_content)
        docs_by_gen = [(doc_other, 10, 'T-sid')]
        st.sync_exchange(
            docs_by_gen, 'other-replica', last_known_generation=0,
            last_known_trans_id=None, return_doc_cb=ignore)
        self.assertGetDoc(self.db, doc.doc_id, other_rev, new_content, False)
        self.assertEqual(
            [doc_other], self.db.get_from_index('test-idx', 'altval'))
        self.assertEqual([], self.db.get_from_index('test-idx', 'value'))


# Use a custom loader to apply the scenarios at load time.
load_tests = tests.load_with_scenarios
