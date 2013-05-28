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
tests for eipconfig
"""
import copy
import json
import os
import unittest

from leap.common.testing.basetest import BaseLeapTest
from leap.services.eip.eipconfig import EIPConfig


sample_config = {
    "gateways": [
    {
        "capabilities": {
            "adblock": False,
            "filter_dns": True,
            "limited": True,
            "ports": [
            "1194",
            "443",
            "53",
            "80"
            ],
        "protocols": [
            "tcp",
            "udp"],
        "transport": [
            "openvpn"],
        "user_ips": False},
    "host": "host.dev.example.org",
    "ip_address": "11.22.33.44",
    "location": "cyberspace"
    }],
    "locations": {
        "ankara": {
        "country_code": "XX",
        "hemisphere": "S",
        "name": "Antarctica",
        "timezone": "+2"
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
    #provider = "testprovider.example.org"

    maxDiff = None

    def setUp(self):
        pass

    def tearDown(self):
        pass

    #
    # helpers
    #

    def write_config(self, data):
        self.configfile = os.path.join(
            self.tempdir, "eipconfig.json")
        conf = open(self.configfile, "w")
        conf.write(json.dumps(data))
        conf.close()

    def test_load_valid_config(self):
        """
        load a sample config
        """
        self.write_config(sample_config)
        config = EIPConfig()
        #self.assertRaises(
            #AssertionError,
            #config.get_clusters)

        self.assertTrue(config.load(
            self.configfile, relative=False))
        self.assertEqual(
            config.get_openvpn_configuration(),
            sample_config["openvpn_configuration"])
        self.assertEqual(
            config.get_gateway_ip(),
            "11.22.33.44")
        self.assertEqual(config.get_version(), 1)
        self.assertEqual(config.get_serial(), 1)
        self.assertEqual(config.get_gateways(),
                         sample_config["gateways"])
        self.assertEqual(
            config.get_clusters(), None)

    def test_sanitize_config(self):
        """
        check the sanitization of options
        """
        # extra parameters
        data = copy.deepcopy(sample_config)
        data['openvpn_configuration']["extra_param"] = "FOO"
        self.write_config(data)
        config = EIPConfig()
        config.load(
            self.configfile, relative=False)
        self.assertEqual(
            config.get_openvpn_configuration(),
            sample_config["openvpn_configuration"])

        # non allowed chars
        data = copy.deepcopy(sample_config)
        data['openvpn_configuration']["auth"] = "SHA1;"
        self.write_config(data)
        config = EIPConfig()
        config.load(self.configfile, relative=False)
        self.assertEqual(
            config.get_openvpn_configuration(),
            sample_config["openvpn_configuration"])

        # non allowed chars
        data = copy.deepcopy(sample_config)
        data['openvpn_configuration']["auth"] = "SHA1>`&|"
        self.write_config(data)
        config = EIPConfig()
        config.load(self.configfile, relative=False)
        self.assertEqual(
            config.get_openvpn_configuration(),
            sample_config["openvpn_configuration"])

        # lowercase
        data = copy.deepcopy(sample_config)
        data['openvpn_configuration']["auth"] = "shaSHA1"
        self.write_config(data)
        config = EIPConfig()
        config.load(self.configfile, relative=False)
        self.assertEqual(
            config.get_openvpn_configuration(),
            sample_config["openvpn_configuration"])

        # all characters invalid -> null value
        data = copy.deepcopy(sample_config)
        data['openvpn_configuration']["auth"] = "sha&*!@#;"
        self.write_config(data)
        config = EIPConfig()
        config.load(self.configfile, relative=False)
        self.assertEqual(
            config.get_openvpn_configuration(),
            {'cipher': 'AES-128-CBC',
             'tls-cipher': 'DHE-RSA-AES128-SHA'})

        # bad_ip
        data = copy.deepcopy(sample_config)
        data['gateways'][0]["ip_address"] = "11.22.33.44;"
        self.write_config(data)
        config = EIPConfig()
        config.load(self.configfile, relative=False)
        self.assertEqual(
            config.get_gateway_ip(),
            None)

        data = copy.deepcopy(sample_config)
        data['gateways'][0]["ip_address"] = "11.22.33.44`"
        self.write_config(data)
        config = EIPConfig()
        config.load(self.configfile, relative=False)
        self.assertEqual(
            config.get_gateway_ip(),
            None)

if __name__ == "__main__":
    unittest.main()
