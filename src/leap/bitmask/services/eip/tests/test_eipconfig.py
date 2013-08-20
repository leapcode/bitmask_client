# -*- coding: utf-8 -*-
# test_eipconfig.py
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
Tests for eipconfig
"""
import copy
import json
import os
import unittest

from leap.bitmask.services.eip.eipconfig import EIPConfig
from leap.bitmask.config.providerconfig import ProviderConfig
from leap.common.testing.basetest import BaseLeapTest

from mock import Mock


sample_config = {
    "gateways": [{
        "capabilities": {
            "adblock": False,
            "filter_dns": True,
            "limited": True,
            "ports": [
                "1194",
                "443",
                "53",
                "80"],
            "protocols": [
                "tcp",
                "udp"],
            "transport": ["openvpn"],
            "user_ips": False},
        "host": "host.dev.example.org",
        "ip_address": "11.22.33.44",
        "location": "cyberspace"
    }, {
        "capabilities": {
            "adblock": False,
            "filter_dns": True,
            "limited": True,
            "ports": [
                "1194",
                "443",
                "53",
                "80"],
            "protocols": [
                "tcp",
                "udp"],
            "transport": ["openvpn"],
            "user_ips": False},
        "host": "host2.dev.example.org",
        "ip_address": "22.33.44.55",
        "location": "cyberspace"
    }
    ],
    "locations": {
        "ankara": {
            "country_code": "XX",
            "hemisphere": "S",
            "name": "Antarctica",
            "timezone": "+2"
        },
        "cyberspace": {
            "country_code": "XX",
            "hemisphere": "X",
            "name": "outer space",
            "timezone": ""
        }
    },
    "openvpn_configuration": {
        "auth": "SHA1",
        "cipher": "AES-128-CBC",
        "tls-cipher": "DHE-RSA-AES128-SHA"
    },
    "serial": 1,
    "version": 1
}


class EIPConfigTest(BaseLeapTest):

    __name__ = "eip_config_tests"

    maxDiff = None

    def setUp(self):
        self._old_ospath_exists = os.path.exists

    def tearDown(self):
        os.path.exists = self._old_ospath_exists

    def _write_config(self, data):
        """
        Helper to write some data to a temp config file.

        :param data: data to be used to save in the config file.
        :data type: dict (valid json)
        """
        self.configfile = os.path.join(self.tempdir, "eipconfig.json")
        conf = open(self.configfile, "w")
        conf.write(json.dumps(data))
        conf.close()

    def _get_eipconfig(self, fromfile=True, data=sample_config, api_ver='1'):
        """
        Helper that returns an EIPConfig object using the data parameter
        or a sample data.

        :param fromfile: sets if we should use a file or a string
        :type fromfile: bool
        :param data: sets the data to be used to load in the EIPConfig object
        :type data: dict (valid json)
        :param api_ver: the api_version schema to use.
        :type api_ver: str
        :rtype: EIPConfig
        """
        config = EIPConfig()
        config.set_api_version(api_ver)

        loaded = False
        if fromfile:
            self._write_config(data)
            loaded = config.load(self.configfile, relative=False)
        else:
            json_string = json.dumps(data)
            loaded = config.load(data=json_string)

        if not loaded:
            return None

        return config

    def test_loads_from_file(self):
        config = self._get_eipconfig()
        self.assertIsNotNone(config)

    def test_loads_from_data(self):
        config = self._get_eipconfig(fromfile=False)
        self.assertIsNotNone(config)

    def test_load_valid_config_from_file(self):
        config = self._get_eipconfig()
        self.assertIsNotNone(config)

        self.assertEqual(
            config.get_openvpn_configuration(),
            sample_config["openvpn_configuration"])

        sample_ip = sample_config["gateways"][0]["ip_address"]
        self.assertEqual(
            config.get_gateway_ip(),
            sample_ip)
        self.assertEqual(config.get_version(), sample_config["version"])
        self.assertEqual(config.get_serial(), sample_config["serial"])
        self.assertEqual(config.get_gateways(), sample_config["gateways"])
        self.assertEqual(config.get_locations(), sample_config["locations"])
        self.assertEqual(config.get_clusters(), None)

    def test_load_valid_config_from_data(self):
        config = self._get_eipconfig(fromfile=False)
        self.assertIsNotNone(config)

        self.assertEqual(
            config.get_openvpn_configuration(),
            sample_config["openvpn_configuration"])

        sample_ip = sample_config["gateways"][0]["ip_address"]
        self.assertEqual(
            config.get_gateway_ip(),
            sample_ip)

        self.assertEqual(config.get_version(), sample_config["version"])
        self.assertEqual(config.get_serial(), sample_config["serial"])
        self.assertEqual(config.get_gateways(), sample_config["gateways"])
        self.assertEqual(config.get_locations(), sample_config["locations"])
        self.assertEqual(config.get_clusters(), None)

    def test_sanitize_extra_parameters(self):
        data = copy.deepcopy(sample_config)
        data['openvpn_configuration']["extra_param"] = "FOO"
        config = self._get_eipconfig(data=data)

        self.assertEqual(
            config.get_openvpn_configuration(),
            sample_config["openvpn_configuration"])

    def test_sanitize_non_allowed_chars(self):
        data = copy.deepcopy(sample_config)
        data['openvpn_configuration']["auth"] = "SHA1;"
        config = self._get_eipconfig(data=data)

        self.assertEqual(
            config.get_openvpn_configuration(),
            sample_config["openvpn_configuration"])

        data = copy.deepcopy(sample_config)
        data['openvpn_configuration']["auth"] = "SHA1>`&|"
        config = self._get_eipconfig(data=data)

        self.assertEqual(
            config.get_openvpn_configuration(),
            sample_config["openvpn_configuration"])

    def test_sanitize_lowercase(self):
        data = copy.deepcopy(sample_config)
        data['openvpn_configuration']["auth"] = "shaSHA1"
        config = self._get_eipconfig(data=data)

        self.assertEqual(
            config.get_openvpn_configuration(),
            sample_config["openvpn_configuration"])

    def test_all_characters_invalid(self):
        data = copy.deepcopy(sample_config)
        data['openvpn_configuration']["auth"] = "sha&*!@#;"
        config = self._get_eipconfig(data=data)

        self.assertEqual(
            config.get_openvpn_configuration(),
            {'cipher': 'AES-128-CBC',
             'tls-cipher': 'DHE-RSA-AES128-SHA'})

    def test_sanitize_bad_ip(self):
        data = copy.deepcopy(sample_config)
        data['gateways'][0]["ip_address"] = "11.22.33.44;"
        config = self._get_eipconfig(data=data)

        self.assertEqual(config.get_gateway_ip(), None)

        data = copy.deepcopy(sample_config)
        data['gateways'][0]["ip_address"] = "11.22.33.44`"
        config = self._get_eipconfig(data=data)

        self.assertEqual(config.get_gateway_ip(), None)

    def test_default_gateway_on_unknown_index(self):
        config = self._get_eipconfig()
        sample_ip = sample_config["gateways"][0]["ip_address"]
        self.assertEqual(config.get_gateway_ip(999), sample_ip)

    def test_get_gateway_by_index(self):
        config = self._get_eipconfig()
        sample_ip_0 = sample_config["gateways"][0]["ip_address"]
        sample_ip_1 = sample_config["gateways"][1]["ip_address"]
        self.assertEqual(config.get_gateway_ip(0), sample_ip_0)
        self.assertEqual(config.get_gateway_ip(1), sample_ip_1)

    def test_get_client_cert_path_as_expected(self):
        config = self._get_eipconfig()
        config.get_path_prefix = Mock(return_value='test')

        provider_config = ProviderConfig()

        # mock 'get_domain' so we don't need to load a config
        provider_domain = 'test.provider.com'
        provider_config.get_domain = Mock(return_value=provider_domain)

        expected_path = os.path.join('test', 'leap', 'providers',
                                     provider_domain, 'keys', 'client',
                                     'openvpn.pem')

        # mock 'os.path.exists' so we don't get an error for unexisting file
        os.path.exists = Mock(return_value=True)
        cert_path = config.get_client_cert_path(provider_config)

        self.assertEqual(cert_path, expected_path)

    def test_get_client_cert_path_about_to_download(self):
        config = self._get_eipconfig()
        config.get_path_prefix = Mock(return_value='test')

        provider_config = ProviderConfig()

        # mock 'get_domain' so we don't need to load a config
        provider_domain = 'test.provider.com'
        provider_config.get_domain = Mock(return_value=provider_domain)

        expected_path = os.path.join('test', 'leap', 'providers',
                                     provider_domain, 'keys', 'client',
                                     'openvpn.pem')

        cert_path = config.get_client_cert_path(
            provider_config, about_to_download=True)

        self.assertEqual(cert_path, expected_path)

    def test_get_client_cert_path_fails(self):
        config = self._get_eipconfig()
        provider_config = ProviderConfig()

        # mock 'get_domain' so we don't need to load a config
        provider_domain = 'test.provider.com'
        provider_config.get_domain = Mock(return_value=provider_domain)

        with self.assertRaises(AssertionError):
            config.get_client_cert_path(provider_config)

    def test_fails_without_api_set(self):
        config = EIPConfig()
        with self.assertRaises(AssertionError):
            config.load('non-relevant-path')

    def test_fails_with_api_without_schema(self):
        with self.assertRaises(AssertionError):
            self._get_eipconfig(api_ver='123')

if __name__ == "__main__":
    unittest.main()
