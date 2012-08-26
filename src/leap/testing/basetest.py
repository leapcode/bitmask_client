import os
import platform
import shutil
import tempfile

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from leap.base.config import get_username, get_groupname

_system = platform.system()


class BaseLeapTest(unittest.TestCase):

    __name__ = "leap_test"

    @classmethod
    def setUpClass(cls):
        cls.old_path = os.environ['PATH']
        cls.old_home = os.environ['HOME']
        cls.tempdir = tempfile.mkdtemp(prefix="leap_tests-")
        cls.home = cls.tempdir
        bin_tdir = os.path.join(
            cls.tempdir,
            'bin')
        os.environ["PATH"] = bin_tdir
        os.environ["HOME"] = cls.tempdir

    @classmethod
    def tearDownClass(cls):
        os.environ["PATH"] = cls.old_path
        os.environ["HOME"] = cls.old_home
        shutil.rmtree(cls.tempdir)

    # you have to override these methods
    # this way we ensure we did not put anything
    # here that you can forget to call.

    def setUp(self):
        raise NotImplementedError("abstract base class")

    def tearDown(self):
        raise NotImplementedError("abstract base class")

    #
    # helper methods
    #

    def get_tempfile(self, filename):
        return os.path.join(self.tempdir, filename)

    def get_username(self):
        return get_username()

    def get_groupname(self):
        return get_groupname()

    def _missing_test_for_plat(self, do_raise=False):
        if do_raise:
            raise NotImplementedError(
                "This test is not implemented "
                "for the running platform: %s" %
                _system)
