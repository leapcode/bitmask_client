import os
import platform
import shutil
import stat
import tempfile
import unittest

from leap.util import fileutil


class FileUtilTest(unittest.TestCase):
    """
    test our file utils
    """

    def setUp(self):
        self.system = platform.system()
        self.create_temp_dir()

    def tearDown(self):
        self.remove_temp_dir()

    #
    # helpers
    #

    def create_temp_dir(self):
        self.tmpdir = tempfile.mkdtemp()

    def remove_temp_dir(self):
        shutil.rmtree(self.tmpdir)

    def get_file_path(self, filename):
        return os.path.join(
            self.tmpdir,
            filename)

    def touch_exec_file(self):
        fp = self.get_file_path('testexec')
        open(fp, 'w').close()
        os.chmod(
            fp,
            stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        return fp

    def get_mode(self, fp):
        return stat.S_IMODE(os.stat(fp).st_mode)

    #
    # tests
    #

    def test_is_user_executable(self):
        """
        touch_exec_file creates in mode 700?
        """
        # XXX could check access X_OK

        fp = self.touch_exec_file()
        mode = self.get_mode(fp)
        self.assertEqual(mode, int('700', 8))

    def test_which(self):
        """
        which implementation ok?
        not a very reliable test,
        but I cannot think of anything smarter now
        I guess it's highly improbable that copy
        """
        # XXX yep, we can change the syspath
        # for the test... !

        if self.system == "Linux":
            self.assertEqual(
                fileutil.which('cp'),
                '/bin/cp')

    def test_mkdir_p(self):
        """
        our own mkdir -p implementation ok?
        """
        testdir = self.get_file_path(
            os.path.join('test', 'foo', 'bar'))
        self.assertEqual(os.path.isdir(testdir), False)
        fileutil.mkdir_p(testdir)
        self.assertEqual(os.path.isdir(testdir), True)

    def test_check_and_fix_urw_only(self):
        """
        ensure check_and_fix_urx_only ok?
        """
        fp = self.touch_exec_file()
        mode = self.get_mode(fp)
        self.assertEqual(mode, int('700', 8))
        fileutil.check_and_fix_urw_only(fp)
        mode = self.get_mode(fp)
        self.assertEqual(mode, int('600', 8))
