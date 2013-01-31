import copy
import datetime
from functools import partial
#import json
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os

from leap.base.config import JSONLeapConfig
from leap.base import pluggableconfig
from leap.testing.basetest import BaseLeapTest

SAMPLE_CONFIG_DICT = {
    'prop_one': 1,
    'prop_uri': "http://example.org",
    'prop_date': '2012-12-12',
}

EXPECTED_CONFIG = {
    'prop_one': 1,
    'prop_uri': "http://example.org",
    'prop_date': datetime.datetime(2012, 12, 12)
}

sample_spec = {
    'description': 'sample schema definition',
    'type': 'object',
    'properties': {
        'prop_one': {
            'type': int,
            'default': 1,
            'required': True
        },
        'prop_uri': {
            'type': str,
            'default': 'http://example.org',
            'required': True,
            'format': 'uri'
        },
        'prop_date': {
            'type': str,
            'default': '2012-12-12',
            'format': 'date'
        }
    }
}


class SampleConfig(JSONLeapConfig):
    spec = sample_spec

    @property
    def slug(self):
        return os.path.expanduser('~/sampleconfig.json')


class TestJSONLeapConfigValidation(BaseLeapTest):
    def setUp(self):
        self.sampleconfig = SampleConfig()
        self.sampleconfig.save()
        self.sampleconfig.load()
        self.config = self.sampleconfig.config

    def tearDown(self):
        if hasattr(self, 'testfile') and os.path.isfile(self.testfile):
            os.remove(self.testfile)

    # tests

    def test_good_validation(self):
        self.sampleconfig.validate(SAMPLE_CONFIG_DICT)

    def test_broken_int(self):
        _config = copy.deepcopy(SAMPLE_CONFIG_DICT)
        _config['prop_one'] = '1'
        self.assertRaises(
            pluggableconfig.ValidationError,
            partial(self.sampleconfig.validate, _config))

    def test_format_property(self):
        # JsonSchema Validator does not check the format property.
        # We should have to extend the Configuration class
        blah = copy.deepcopy(SAMPLE_CONFIG_DICT)
        blah['prop_uri'] = 'xxx'
        self.assertRaises(
            pluggableconfig.TypeCastException,
            partial(self.sampleconfig.validate, blah))


if __name__ == "__main__":
    unittest.main()
