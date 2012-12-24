import unittest2 as unittest
import tempfile
import shutil

class TestCase(unittest.TestCase):

    def createTempDir(self, prefix='u1db-tmp-'):
        """Create a temporary directory to do some work in.

        This directory will be scheduled for cleanup when the test ends.
        """
        tempdir = tempfile.mkdtemp(prefix=prefix)
        self.addCleanup(shutil.rmtree, tempdir)
        return tempdir

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

    def assertGetDocConflicts(self, db, doc_id, conflicts):
        """Assert what conflicts are stored for a given doc_id.

        :param conflicts: A list of (doc_rev, content) pairs.
            The first item must match the first item returned from the
            database, however the rest can be returned in any order.
        """
        if conflicts:
            conflicts = [(rev, (json.loads(cont) if isinstance(cont, basestring)
                           else cont)) for (rev, cont) in conflicts]
            conflicts = conflicts[:1] + sorted(conflicts[1:])
        actual = db.get_doc_conflicts(doc_id)
        if actual:
            actual = [(doc.rev, (json.loads(doc.get_json())
                   if doc.get_json() is not None else None)) for doc in actual]
            actual = actual[:1] + sorted(actual[1:])
        self.assertEqual(conflicts, actual)

