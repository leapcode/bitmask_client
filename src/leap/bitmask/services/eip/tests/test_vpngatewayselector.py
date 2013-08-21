# -*- coding: utf-8 -*-
# test_vpngatewayselector.py
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
tests for vpngatewayselector
"""

import unittest
import time

from leap.bitmask.services.eip.eipconfig import EIPConfig, VPNGatewaySelector
from leap.common.testing.basetest import BaseLeapTest

from mock import Mock


sample_gateways = [
    {u'host': u'gateway1.com',
     u'ip_address': u'1.2.3.4',
     u'location': u'location1'},
    {u'host': u'gateway2.com',
     u'ip_address': u'2.3.4.5',
     u'location': u'location2'},
    {u'host': u'gateway3.com',
     u'ip_address': u'3.4.5.6',
     u'location': u'location3'},
    {u'host': u'gateway4.com',
     u'ip_address': u'4.5.6.7',
     u'location': u'location4'}
]

sample_gateways_no_location = [
    {u'host': u'gateway1.com',
     u'ip_address': u'1.2.3.4'},
    {u'host': u'gateway2.com',
     u'ip_address': u'2.3.4.5'},
    {u'host': u'gateway3.com',
     u'ip_address': u'3.4.5.6'}
]

sample_locations = {
    u'location1': {u'timezone': u'2'},
    u'location2': {u'timezone': u'-7'},
    u'location3': {u'timezone': u'-4'},
    u'location4': {u'timezone': u'+13'}
}

# 0 is not used, only for indexing from 1 in tests
ips = (0, u'1.2.3.4', u'2.3.4.5', u'3.4.5.6', u'4.5.6.7')


class VPNGatewaySelectorTest(BaseLeapTest):
    """
    VPNGatewaySelector's tests.
    """
    def setUp(self):
        self.eipconfig = EIPConfig()
        self.eipconfig.get_gateways = Mock(return_value=sample_gateways)
        self.eipconfig.get_locations = Mock(return_value=sample_locations)

    def tearDown(self):
        pass

    def test_get_no_gateways(self):
        gateway_selector = VPNGatewaySelector(self.eipconfig)
        self.eipconfig.get_gateways = Mock(return_value=[])
        gateways = gateway_selector.get_gateways()
        self.assertEqual(gateways, [])

    def test_get_gateway_with_no_locations(self):
        gateway_selector = VPNGatewaySelector(self.eipconfig)
        self.eipconfig.get_gateways = Mock(
            return_value=sample_gateways_no_location)
        self.eipconfig.get_locations = Mock(return_value=[])
        gateways = gateway_selector.get_gateways()
        gateways_default_order = [
            sample_gateways[0]['ip_address'],
            sample_gateways[1]['ip_address'],
            sample_gateways[2]['ip_address']
        ]
        self.assertEqual(gateways, gateways_default_order)

    def test_correct_order_gmt(self):
        gateway_selector = VPNGatewaySelector(self.eipconfig, 0)
        gateways = gateway_selector.get_gateways()
        self.assertEqual(gateways, [ips[1], ips[3], ips[2], ips[4]])

    def test_correct_order_gmt_minus_3(self):
        gateway_selector = VPNGatewaySelector(self.eipconfig, -3)
        gateways = gateway_selector.get_gateways()
        self.assertEqual(gateways, [ips[3], ips[2], ips[1], ips[4]])

    def test_correct_order_gmt_minus_7(self):
        gateway_selector = VPNGatewaySelector(self.eipconfig, -7)
        gateways = gateway_selector.get_gateways()
        self.assertEqual(gateways, [ips[2], ips[3], ips[4], ips[1]])

    def test_correct_order_gmt_plus_5(self):
        gateway_selector = VPNGatewaySelector(self.eipconfig, 5)
        gateways = gateway_selector.get_gateways()
        self.assertEqual(gateways, [ips[1], ips[4], ips[3], ips[2]])

    def test_correct_order_gmt_plus_12(self):
        gateway_selector = VPNGatewaySelector(self.eipconfig, 12)
        gateways = gateway_selector.get_gateways()
        self.assertEqual(gateways, [ips[4], ips[2], ips[3], ips[1]])

    def test_correct_order_gmt_minus_11(self):
        gateway_selector = VPNGatewaySelector(self.eipconfig, -11)
        gateways = gateway_selector.get_gateways()
        self.assertEqual(gateways, [ips[4], ips[2], ips[3], ips[1]])

    def test_correct_order_gmt_plus_14(self):
        gateway_selector = VPNGatewaySelector(self.eipconfig, 14)
        gateways = gateway_selector.get_gateways()
        self.assertEqual(gateways, [ips[4], ips[2], ips[3], ips[1]])


class VPNGatewaySelectorDSTTest(VPNGatewaySelectorTest):
    """
    VPNGatewaySelector's tests.
    It uses the opposite value of the current DST.
    """
    def setUp(self):
        self._original_daylight = time.daylight
        time.daylight = not time.daylight
        VPNGatewaySelectorTest.setUp(self)

    def tearDown(self):
        VPNGatewaySelectorTest.tearDown(self)
        time.daylight = self._original_daylight

if __name__ == "__main__":
    unittest.main()
