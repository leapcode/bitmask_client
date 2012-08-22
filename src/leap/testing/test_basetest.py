"""becase it's oh so meta"""
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import os
import StringIO

from leap.testing.basetest import BaseLeapTest

# global for tempdir checking
_tempdir = None


class TestCaseRunner(object):
    def run_testcase(self, testcase):
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(testcase)

        # Create runner, and run testcase
        io = StringIO.StringIO()
        runner = unittest.TextTestRunner(stream=io)
        results = runner.run(suite)
        return results


class TestAbstractBaseLeapTest(unittest.TestCase, TestCaseRunner):

    def test_abstract_base_class(self):
        class _BaseTest(BaseLeapTest):
            def test_dummy_method(self):
                pass

            def test_tautology(self):
                assert True

        results = self.run_testcase(_BaseTest)

        # should be 2 errors: NotImplemented
        # raised for setUp/tearDown
        self.assertEquals(results.testsRun, 2)
        self.assertEquals(len(results.failures), 0)
        self.assertEquals(len(results.errors), 2)


class TestInitBaseLeapTest(BaseLeapTest):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_path_is_changed(self):
        os_path = os.environ['PATH']
        self.assertTrue(os_path.startswith(self.tempdir))

    def test_old_path_is_saved(self):
        self.assertTrue(len(self.old_path) > 1)


class TestCleanedBaseLeapTest(unittest.TestCase, TestCaseRunner):

    def test_tempdir_is_cleaned_after_tests(self):
        class _BaseTest(BaseLeapTest):
            def setUp(self):
                global _tempdir
                _tempdir = self.tempdir

            def tearDown(self):
                pass

            def test_tempdir_created(self):
                self.assertTrue(os.path.isdir(self.tempdir))

            def test_tempdir_created_on_setupclass(self):
                self.assertEqual(_tempdir, self.tempdir)

        results = self.run_testcase(_BaseTest)
        self.assertEquals(results.testsRun, 2)
        self.assertEquals(len(results.failures), 0)
        self.assertEquals(len(results.errors), 0)

        # did we cleaned the tempdir?
        self.assertFalse(os.path.isdir(_tempdir))

if __name__ == "__main__":
    unittest.main()
