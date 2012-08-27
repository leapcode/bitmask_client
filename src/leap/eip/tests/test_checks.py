import json
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os

from mock import Mock

from leap.base import config as baseconfig
from leap.eip import checks as eipchecks
from leap.eip import constants as eipconstants
from leap.testing.basetest import BaseLeapTest


class EIPCheckTest(BaseLeapTest):

    __name__ = "eip_check_tests"

    def setUp(self):
        pass

    def tearDown(self):
        pass

    # test methods are there, and can be called from run_all

    def test_checker_should_implement_check_methods(self):
        checker = eipchecks.EIPChecker()

        self.assertTrue(hasattr(checker, "check_default_eipconfig"),
                        "missing meth")
        self.assertTrue(hasattr(checker, "check_is_there_default_provider"),
                        "missing meth")
        self.assertTrue(hasattr(checker, "fetch_definition"), "missing meth")
        self.assertTrue(hasattr(checker, "fetch_eip_config"), "missing meth")
        self.assertTrue(hasattr(checker, "check_complete_eip_config"),
                        "missing meth")
        self.assertTrue(hasattr(checker, "ping_gateway"), "missing meth")

    def test_checker_should_actually_call_all_tests(self):
        checker = eipchecks.EIPChecker()

        mc = Mock()
        checker.run_all(checker=mc)
        self.assertTrue(mc.check_default_eipconfig.called, "not called")
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

    # test individual check methods

    def test_dump_default_eipconfig(self):
        checker = eipchecks.EIPChecker()
        # no eip config (empty home)
        eipconfig = baseconfig.get_config_file(eipconstants.EIP_CONFIG)
        self.assertFalse(os.path.isfile(eipconfig))
        checker.check_default_eipconfig()
        # we've written one, so it should be there.
        self.assertTrue(os.path.isfile(eipconfig))
        with open(eipconfig, 'rb') as fp:
            deserialized = json.load(fp)
        self.assertEqual(deserialized,
                         eipconstants.EIP_SAMPLE_JSON)
        # TODO: when new JSONConfig class is in place, we shold
        # run validation methods.


if __name__ == "__main__":
    unittest.main()
