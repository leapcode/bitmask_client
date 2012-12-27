import unittest2
from leap.soledad.backends.couch import CouchDatabase
from leap.soledad.backends.leap_backend import LeapDocument
from u1db import errors, vectorclock

try:
    import simplejson as json
except ImportError:
    import json  # noqa

simple_doc = '{"key": "value"}'
nested_doc = '{"key": "value", "sub": {"doc": "underneath"}}'

def make_document_for_test(test, doc_id, rev, content, has_conflicts=False):
    return LeapDocument(doc_id, rev, content, has_conflicts=has_conflicts)

class CouchTestCase(unittest2.TestCase):

    def setUp(self):
        self.db = CouchDatabase('http://localhost:5984', 'u1db_tests')

    def make_document(self, doc_id, doc_rev, content, has_conflicts=False):
        return self.make_document_for_test(
            self, doc_id, doc_rev, content, has_conflicts)

    def make_document_for_test(self, test, doc_id, doc_rev, content,
                               has_conflicts):
        return make_document_for_test(
            test, doc_id, doc_rev, content, has_conflicts)

    def assertGetDoc(self, db, doc_id, doc_rev, content, has_conflicts):
        """Assert that the document in the database looks correct."""
        exp_doc = self.make_document(doc_id, doc_rev, content,
                                     has_conflicts=has_conflicts)
        self.assertEqual(exp_doc, db.get_doc(doc_id))

    def assertGetDocIncludeDeleted(self, db, doc_id, doc_rev, content,
                                   has_conflicts):
        """Assert that the document in the database looks correct."""
        exp_doc = self.make_document(doc_id, doc_rev, content,
                                     has_conflicts=has_conflicts)
        self.assertEqual(exp_doc, db.get_doc(doc_id, include_deleted=True))


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



    def tearDown(self):
        self.db._server.delete('u1db_tests')

if __name__ == '__main__':
    unittest2.main()
