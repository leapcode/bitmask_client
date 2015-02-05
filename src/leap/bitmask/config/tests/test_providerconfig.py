# -*- coding: utf-8 -*-
# test_providerconfig.py
# Copyright (C) 2013 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Tests for providerconfig
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import os
import json
import copy

from leap.bitmask.config.providerconfig import ProviderConfig, MissingCACert
from leap.bitmask.services import get_supported
from leap.common.testing.basetest import BaseLeapTest

from mock import Mock


sample_config = {
    "api_uri": "https://api.test.bitmask.net:4430",
    "api_version": "1",
    "ca_cert_fingerprint":
    "SHA256: 0f17c033115f6b76ff67871872303ff65034efe7dd1b910062ca323eb4da5c7e",
    "ca_cert_uri": "https://test.bitmask.net/ca.crt",
    "default_language": "en",
    "description": {
        "en": "Test description for provider",
        "es": "Descripcion de prueba para el proveedor"
    },
    "domain": "test.bitmask.net",
    "enrollment_policy": "open",
    "languages": [
        "en",
        "es"
    ],
    "name": {
        "en": "Bitmask testing environment",
        "es": "Entorno de pruebas de Bitmask"
    },
    "service": {
        "allow_anonymous": True,
        "allow_free": True,
        "allow_limited_bandwidth": True,
        "allow_paid": False,
        "allow_registration": True,
        "allow_unlimited_bandwidth": False,
        "bandwidth_limit": 400000,
        "default_service_level": 1,
        "levels": [
            {
                "bandwidth": "limited",
                "id": 1,
                "name": "anonymous"
            },
            {
                "bandwidth": "limited",
                "id": 2,
                "name": "free",
                "storage": 50
            }
        ]
    },
    "services": [
        "openvpn"
    ]
}


class ProviderConfigTest(BaseLeapTest):
    """Tests for ProviderConfig"""

    def setUp(self):
        self._provider_config = ProviderConfig()
        json_string = json.dumps(sample_config)
        self._provider_config.load(data=json_string)

        # At certain points we are going to be replacing these method
        # to avoid creating a file.
        # We need to save the old implementation and restore it in
        # tearDown so we are sure everything is as expected for each
        # test. If we do it inside each specific test, a failure in
        # the test will leave the implementation with the mock.
        self._old_ospath_exists = os.path.exists

    def tearDown(self):
        os.path.exists = self._old_ospath_exists

    def test_configs_ok(self):
        """
        Test if the configs loads ok
        """
        # TODO: this test should go to the BaseConfig tests
        pc = self._provider_config
        self.assertEqual(pc.get_api_uri(), sample_config['api_uri'])
        self.assertEqual(pc.get_api_version(), sample_config['api_version'])
        self.assertEqual(pc.get_ca_cert_fingerprint(),
                         sample_config['ca_cert_fingerprint'])
        self.assertEqual(pc.get_ca_cert_uri(), sample_config['ca_cert_uri'])
        self.assertEqual(pc.get_default_language(),
                         sample_config['default_language'])

        self.assertEqual(pc.get_domain(), sample_config['domain'])
        self.assertEqual(pc.get_enrollment_policy(),
                         sample_config['enrollment_policy'])
        self.assertEqual(pc.get_languages(), sample_config['languages'])

    def test_localizations(self):
        pc = self._provider_config

        self.assertEqual(pc.get_description(lang='en'),
                         sample_config['description']['en'])
        self.assertEqual(pc.get_description(lang='es'),
                         sample_config['description']['es'])

        self.assertEqual(pc.get_name(lang='en'), sample_config['name']['en'])
        self.assertEqual(pc.get_name(lang='es'), sample_config['name']['es'])

    def _localize(self, lang):
        """
        Helper to change default language of the provider config.
        """
        pc = self._provider_config
        config = copy.deepcopy(sample_config)
        config['default_language'] = lang
        json_string = json.dumps(config)
        pc.load(data=json_string)

        return config

    def test_default_localization1(self):
        pc = self._provider_config
        config = self._localize(sample_config['languages'][0])

        default_language = config['default_language']
        default_description = config['description'][default_language]
        default_name = config['name'][default_language]

        self.assertEqual(pc.get_description(lang='xx'), default_description)
        self.assertEqual(pc.get_description(), default_description)

        self.assertEqual(pc.get_name(lang='xx'), default_name)
        self.assertEqual(pc.get_name(), default_name)

    def test_default_localization2(self):
        pc = self._provider_config
        config = self._localize(sample_config['languages'][1])

        default_language = config['default_language']
        default_description = config['description'][default_language]
        default_name = config['name'][default_language]

        self.assertEqual(pc.get_description(lang='xx'), default_description)
        self.assertEqual(pc.get_description(), default_description)

        self.assertEqual(pc.get_name(lang='xx'), default_name)
        self.assertEqual(pc.get_name(), default_name)

    def test_get_ca_cert_path_as_expected(self):
        pc = self._provider_config

        provider_domain = sample_config['domain']
        expected_path = os.path.join('leap', 'providers',
                                     provider_domain, 'keys', 'ca',
                                     'cacert.pem')

        # mock 'os.path.exists' so we don't get an error for unexisting file
        os.path.exists = Mock(return_value=True)
        cert_path = pc.get_ca_cert_path()

        self.assertTrue(cert_path.endswith(expected_path))

    def test_get_ca_cert_path_about_to_download(self):
        pc = self._provider_config

        provider_domain = sample_config['domain']
        expected_path = os.path.join('leap', 'providers',
                                     provider_domain, 'keys', 'ca',
                                     'cacert.pem')

        cert_path = pc.get_ca_cert_path(about_to_download=True)
        self.assertTrue(cert_path.endswith(expected_path))

    def test_get_ca_cert_path_fails(self):
        pc = self._provider_config

        # mock 'get_domain' so we don't need to load a config
        provider_domain = 'test.provider.com'
        pc.get_domain = Mock(return_value=provider_domain)

        with self.assertRaises(MissingCACert):
            pc.get_ca_cert_path()

    def test_provides_eip(self):
        pc = self._provider_config
        config = copy.deepcopy(sample_config)

        # It provides
        config['services'] = ['openvpn', 'test_service']
        json_string = json.dumps(config)
        pc.load(data=json_string)
        self.assertTrue(pc.provides_eip())

        # It does not provides
        config['services'] = ['test_service', 'other_service']
        json_string = json.dumps(config)
        pc.load(data=json_string)
        self.assertFalse(pc.provides_eip())

    def test_provides_mx(self):
        pc = self._provider_config
        config = copy.deepcopy(sample_config)

        # It provides
        config['services'] = ['mx', 'other_service']
        json_string = json.dumps(config)
        pc.load(data=json_string)
        self.assertTrue(pc.provides_mx())

        # It does not provides
        config['services'] = ['test_service', 'other_service']
        json_string = json.dumps(config)
        pc.load(data=json_string)
        self.assertFalse(pc.provides_mx())

    def test_supports_unknown_service(self):
        pc = self._provider_config
        config = copy.deepcopy(sample_config)

        config['services'] = ['unknown']
        json_string = json.dumps(config)
        pc.load(data=json_string)
        self.assertFalse('unknown' in get_supported(pc.get_services()))

    def test_provides_unknown_service(self):
        pc = self._provider_config
        config = copy.deepcopy(sample_config)

        config['services'] = ['unknown']
        json_string = json.dumps(config)
        pc.load(data=json_string)
        self.assertTrue('unknown' in pc.get_services())


if __name__ == "__main__":
    unittest.main()
