
"""Test config helper functions"""

import unittest

from leap.eip import config

class TestConfig(unittest.TestCase):
    """
    Test configuration help functions.
    """
    def test_get_config_json(self):
        config_js = config.get_config_json()
        self.assertTrue(isinstance(config_js, dict))
        self.assertTrue(config_js.has_key('transport'))
        self.assertTrue(config_js.has_key('provider'))
        self.assertEqual(config_js['provider'], "testprovider.org")

