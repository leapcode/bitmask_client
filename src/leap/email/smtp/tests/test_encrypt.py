import os
import unittest
import gnupg

class EncryptMessageTestCase(unittest.TestCase):

    def test_encrypt_to_signonly(self):
        plaintext = BytesIO(b'Hello World\n')
        ciphertext = BytesIO()
        ctx = gpgme.Context()
        recipient = ctx.get_key('15E7CE9BF1771A4ABC550B31F540A569CB935A42')
        try:
            ctx.encrypt([recipient], gpgme.ENCRYPT_ALWAYS_TRUST,
                        plaintext, ciphertext)
        except gpgme.GpgmeError as exc:
            self.assertEqual(exc.args[0], gpgme.ERR_SOURCE_UNKNOWN)
            self.assertEqual(exc.args[1], gpgme.ERR_GENERAL)
        else:
            self.fail('gpgme.GpgmeError not raised')


def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromName(__name__)

