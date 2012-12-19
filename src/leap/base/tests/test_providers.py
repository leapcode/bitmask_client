import copy
import json
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os

import jsonschema

#from leap import __branding as BRANDING
from leap.testing.basetest import BaseLeapTest
from leap.base import providers


EXPECTED_DEFAULT_CONFIG = {
    u"api_version": u"0.1.0",
    u"description": {u'en': u"Test provider"},
    u"default_language": u"en",
    #u"display_name": {u'en': u"Test Provider"},
    u"domain": u"testprovider.example.org",
    u'name': {u'en': u'Test Provider'},
    u"enrollment_policy": u"open",
    #u"serial": 1,
    u"services": [
        u"eip"
    ],
    u"languages": [u"en"],
    u"version": u"0.1.0"
}


class TestLeapProviderDefinition(BaseLeapTest):
    def setUp(self):
        self.domain = "testprovider.example.org"
        self.definition = providers.LeapProviderDefinition(
            domain=self.domain)
        self.definition.save(force=True)
        self.definition.load()  # why have to load after save??
        self.config = self.definition.config

    def tearDown(self):
        if hasattr(self, 'testfile') and os.path.isfile(self.testfile):
            os.remove(self.testfile)

    # tests

    # XXX most of these tests can be made more abstract
    # and moved to test_baseconfig *triangulate!*

    def test_provider_slug_property(self):
        slug = self.definition.slug
        self.assertEquals(
            slug,
            os.path.join(
                self.home,
                '.config', 'leap', 'providers',
                '%s' % self.domain,
                'provider.json'))
        with self.assertRaises(AttributeError):
            self.definition.slug = 23

    def test_provider_dump(self):
        # check a good provider definition is dumped to disk
        self.testfile = self.get_tempfile('test.json')
        self.definition.save(to=self.testfile, force=True)
        deserialized = json.load(open(self.testfile, 'rb'))
        self.maxDiff = None
        self.assertEqual(deserialized, EXPECTED_DEFAULT_CONFIG)

    def test_provider_dump_to_slug(self):
        # same as above, but we test the ability to save to a
        # file generated from the slug.
        # XXX THIS TEST SHOULD MOVE TO test_baseconfig
        self.definition.save()
        filename = self.definition.filename
        self.assertTrue(os.path.isfile(filename))
        deserialized = json.load(open(filename, 'rb'))
        self.assertEqual(deserialized, EXPECTED_DEFAULT_CONFIG)

    def test_provider_load(self):
        # check loading provider from disk file
        self.testfile = self.get_tempfile('test_load.json')
        with open(self.testfile, 'w') as wf:
            wf.write(json.dumps(EXPECTED_DEFAULT_CONFIG))
        self.definition.load(fromfile=self.testfile)
        self.assertDictEqual(self.config,
                             EXPECTED_DEFAULT_CONFIG)

    def test_provider_validation(self):
        self.definition.validate(self.config)
        _config = copy.deepcopy(self.config)
        # bad type, raise validation error
        _config['domain'] = 111
        with self.assertRaises(jsonschema.ValidationError):
            self.definition.validate(_config)

    @unittest.skip
    def test_load_malformed_json_definition(self):
        raise NotImplementedError

    @unittest.skip
    def test_type_validation(self):
        # check various type validation
        # type cast
        raise NotImplementedError


class TestLeapProviderSet(BaseLeapTest):

    def setUp(self):
        self.providers = providers.LeapProviderSet()

    def tearDown(self):
        pass
    ###

    def test_get_zero_count(self):
        self.assertEqual(self.providers.count, 0)

    @unittest.skip
    def test_count_defined_providers(self):
        # check the method used for making
        # the list of providers
        raise NotImplementedError

    @unittest.skip
    def test_get_default_provider(self):
        raise NotImplementedError

    @unittest.skip
    def test_should_be_at_least_one_provider_after_init(self):
        # when we init an empty environment,
        # there should be at least one provider,
        # that will be a dump of the default provider definition
        # somehow a high level test
        raise NotImplementedError

    @unittest.skip
    def test_get_eip_remote_from_default_provider(self):
        # from: default provider
        # expect: remote eip domain
        raise NotImplementedError

if __name__ == "__main__":
    unittest.main()
