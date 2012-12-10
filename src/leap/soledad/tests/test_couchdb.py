import unittest
from soledad.backends.couch import CouchDatabase

class CouchTestCase(unittest.TestCase):

    def setUp(self):
        self._db = CouchDatabase('http://localhost:5984', 'u1db_tests')

    def test_create_get(self):
        doc1 = self._db.create_doc({"key": "value"}, doc_id="testdoc")
        doc2 = self._db.get_doc('testdoc')
        self.assertEqual(doc1, doc2, 'error storing/retrieving document.')
        self.assertEqual(self._db._get_generation(), 1)

    def tearDown(self):
        self._db._server.delete('u1db_tests')

if __name__ == '__main__':
    unittest.main()
