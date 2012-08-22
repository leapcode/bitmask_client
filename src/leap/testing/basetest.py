import os
import shutil
import tempfile

try:
    import unittest2 as unittest
except ImportError:
    import unittest


class BaseLeapTest(unittest.TestCase):

    __name__ = "leap_test"

    @classmethod
    def setUpClass(cls):
        cls.old_path = os.environ['PATH']
        cls.tempdir = tempfile.mkdtemp()
        bin_tdir = os.path.join(
            cls.tempdir,
            'bin')
        os.environ["PATH"] = bin_tdir

    @classmethod
    def tearDownClass(cls):
        os.environ["PATH"] = cls.old_path
        shutil.rmtree(cls.tempdir)

    def setUp(self):
        raise NotImplementedError("abstract base class")

    def tearDown(self):
        raise NotImplementedError("abstract base class")


if __name__ == "__main__":
    unittest.main()
