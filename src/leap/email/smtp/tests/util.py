# copied from pygpgme's tests
import os
import shutil
import tempfile
import unittest

import gpgme

import smtprelay

__all__ = ['GpgHomeTestCase']

keydir = os.path.join(os.path.dirname(__file__), 'keys')

class GpgHomeTestCase(unittest.TestCase):

    gpg_conf_contents = ''
    import_keys = []

    def keyfile(self, key):
        return open(os.path.join(keydir, key), 'rb')

    def setUp(self):
        self._gpghome = tempfile.mkdtemp(prefix='tmp.gpghome')

        # import requested keys into the keyring
        ctx = gpgme.Context()
        for key in self.import_keys:
            with self.keyfile(key) as fp:
                ctx.import_(fp)

    def tearDown(self):
        del os.environ['GNUPGHOME']
        shutil.rmtree(self._gpghome, ignore_errors=True)
