try:
    import simplejson as json
except ImportError:
    import json  # noqa

import unittest
import os

import u1db
from soledad import leap

class EncryptedSyncTestCase(unittest.TestCase):

    PREFIX = '/var/tmp'
    db1_path = "%s/db1.u1db" % PREFIX
    db2_path = "%s/db2.u1db" % PREFIX

    def setUp(self):
        self.db1 = u1db.open(self.db1_path, create=True,
                             document_factory=leap.LeapDocument)
        self.db2 = u1db.open(self.db2_path, create=True,
                             document_factory=leap.LeapDocument)

    def tearDown(self):
        os.unlink(self.db1_path)
        os.unlink(self.db2_path)

    def test_encoding(self):
        doc1 = self.db1.create_doc({ 'key' : 'val' })
        enc1 = doc1.get_encrypted_json()
        doc2 = leap.LeapDocument(doc_id=doc1.doc_id, json=doc1.get_json())
        enc2 = doc2.get_encrypted_json()
        self.assertEqual(enc1, enc2, 'incorrect document encoding')

if __name__ == '__main__':
    unittest.main()
