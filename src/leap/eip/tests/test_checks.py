try:
    import unittest2 as unittest
except ImportError:
    import unittest

from mock import Mock

from leap.eip import checks as eip_checks
from leap.testing.basetest import BaseLeapTest


class EIPCheckTest(BaseLeapTest):

    __name__ = "eip_check_tests"

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_checker_should_implement_check_methods(self):
        checker = eip_checks.EIPChecker()

        self.assertTrue(hasattr(checker, "dump_default_eipconfig"),
                        "missing meth")
        self.assertTrue(hasattr(checker, "check_is_there_default_provider"),
                        "missing meth")
        self.assertTrue(hasattr(checker, "fetch_definition"), "missing meth")
        self.assertTrue(hasattr(checker, "fetch_eip_config"), "missing meth")
        self.assertTrue(hasattr(checker, "check_complete_eip_config"),
                        "missing meth")
        self.assertTrue(hasattr(checker, "ping_gateway"), "missing meth")

    def test_checker_should_actually_call_all_tests(self):
        checker = eip_checks.EIPChecker()

        mc = Mock()
        checker.do_all_checks(checker=mc)
        self.assertTrue(mc.dump_default_eipconfig.called, "not called")
        self.assertTrue(mc.check_is_there_default_provider.called,
                        "not called")
        self.assertTrue(mc.fetch_definition.called,
                        "not called")
        self.assertTrue(mc.fetch_eip_config.called,
                        "not called")
        self.assertTrue(mc.check_complete_eip_config.called,
                        "not called")
        self.assertTrue(mc.ping_gateway.called,
                        "not called")


if __name__ == "__main__":
    unittest.main()
