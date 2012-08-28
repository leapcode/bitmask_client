import copy
import json
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os

from mock import patch, Mock

import requests

from leap.base import config as baseconfig
from leap.base.constants import (DEFAULT_PROVIDER_DEFINITION,
                                 DEFINITION_EXPECTED_PATH)
from leap.eip import checks as eipchecks
from leap.eip import constants as eipconstants
from leap.eip import exceptions as eipexceptions
from leap.testing.basetest import BaseLeapTest


class EIPCheckTest(BaseLeapTest):

    __name__ = "eip_check_tests"

    def setUp(self):
        pass

    def tearDown(self):
        pass

    # test methods are there, and can be called from run_all

    def test_checker_should_implement_check_methods(self):
        checker = eipchecks.EIPConfigChecker()

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
        checker = eipchecks.EIPConfigChecker()

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
        #self.assertTrue(mc.ping_gateway.called,
                        #"not called")

    # test individual check methods

    def test_check_default_eipconfig(self):
        checker = eipchecks.EIPConfigChecker()
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

    def test_check_is_there_default_provider(self):
        checker = eipchecks.EIPConfigChecker()
        # we do dump a sample eip config, but lacking a
        # default provider entry.
        # This error will be possible catched in a different
        # place, when JSONConfig does validation of required fields.

        sampleconfig = copy.copy(eipconstants.EIP_SAMPLE_JSON)
        # blank out default_provider
        sampleconfig['provider'] = None
        eipcfg_path = checker._get_default_eipconfig_path()
        with open(eipcfg_path, 'w') as fp:
            json.dump(sampleconfig, fp)
        with self.assertRaises(eipexceptions.EIPMissingDefaultProvider):
            checker.check_is_there_default_provider()

        sampleconfig = eipconstants.EIP_SAMPLE_JSON
        eipcfg_path = checker._get_default_eipconfig_path()
        with open(eipcfg_path, 'w') as fp:
            json.dump(sampleconfig, fp)
        self.assertTrue(checker.check_is_there_default_provider())

    def test_fetch_definition(self):
        with patch.object(requests, "get") as mocked_get:
            mocked_get.return_value.status_code = 200
            mocked_get.return_value.json = DEFAULT_PROVIDER_DEFINITION
            checker = eipchecks.EIPConfigChecker(fetcher=requests)
            sampleconfig = eipconstants.EIP_SAMPLE_JSON
            checker.fetch_definition(config=sampleconfig)

        fn = os.path.join(baseconfig.get_default_provider_path(),
                          DEFINITION_EXPECTED_PATH)
        with open(fn, 'r') as fp:
            deserialized = json.load(fp)
        self.assertEqual(DEFAULT_PROVIDER_DEFINITION, deserialized)

        # XXX TODO check for ConnectionError, HTTPError, InvalidUrl
        # (and proper EIPExceptions are raised).
        # Look at base.test_config.

    def test_fetch_eip_config(self):
        with patch.object(requests, "get") as mocked_get:
            mocked_get.return_value.status_code = 200
            mocked_get.return_value.json = eipconstants.EIP_SAMPLE_SERVICE
            checker = eipchecks.EIPConfigChecker(fetcher=requests)
            sampleconfig = eipconstants.EIP_SAMPLE_JSON
            checker.fetch_definition(config=sampleconfig)

    def test_check_complete_eip_config(self):
        checker = eipchecks.EIPConfigChecker()
        with self.assertRaises(eipexceptions.EIPConfigurationError):
            sampleconfig = copy.copy(eipconstants.EIP_SAMPLE_JSON)
            sampleconfig['provider'] = None
            checker.check_complete_eip_config(config=sampleconfig)
        with self.assertRaises(eipexceptions.EIPConfigurationError):
            sampleconfig = copy.copy(eipconstants.EIP_SAMPLE_JSON)
            del sampleconfig['provider']
            checker.check_complete_eip_config(config=sampleconfig)

        # normal case
        sampleconfig = copy.copy(eipconstants.EIP_SAMPLE_JSON)
        checker.check_complete_eip_config(config=sampleconfig)

if __name__ == "__main__":
    unittest.main()
