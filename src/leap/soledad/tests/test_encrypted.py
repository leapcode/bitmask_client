from leap.soledad.backends.leap_backend import LeapDocument
from leap.soledad.tests import BaseSoledadTest


class EncryptedSyncTestCase(BaseSoledadTest):

    def test_get_set_encrypted(self):
        doc1 = LeapDocument(soledad=self._soledad)
        doc1.content = {'key': 'val'}
        doc2 = LeapDocument(doc_id=doc1.doc_id,
                            encrypted_json=doc1.get_encrypted_json(),
                            soledad=self._soledad)
        res1 = doc1.get_json()
        res2 = doc2.get_json()
        self.assertEqual(res1, res2, 'incorrect document encryption')
