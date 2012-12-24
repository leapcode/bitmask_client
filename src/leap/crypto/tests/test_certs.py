import unittest

from leap.testing.https_server import where
from leap.crypto import certs


class CertTestCase(unittest.TestCase):

    def test_can_load_client_and_pkey(self):
        with open(where('leaptestscert.pem')) as cf:
            cs = cf.read()
        with open(where('leaptestskey.pem')) as kf:
            ks = kf.read()
        certs.can_load_cert_and_pkey(cs + ks)

        with self.assertRaises(certs.BadCertError):
            # screw header
            certs.can_load_cert_and_pkey(cs.replace("BEGIN", "BEGINN") + ks)


if __name__ == "__main__":
    unittest.main()
