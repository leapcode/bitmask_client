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

from leap.services.eip.eipconfig import EIPConfig, VPNGatewaySelector
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
     u'location': u'location3'}
]

sample_locations = {
    u'location1': {u'timezone': u'2'},
    u'location2': {u'timezone': u'-7'},
    u'location3': {u'timezone': u'-4'}
}


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

    def test_correct_order_gmt(self):
        gateway_selector = VPNGatewaySelector(self.eipconfig, 0)
        gateways = gateway_selector.get_gateways()
        self.assertEqual(gateways, [u'1.2.3.4', u'3.4.5.6', u'2.3.4.5'])

    def test_correct_order_gmt_minus_3(self):
        gateway_selector = VPNGatewaySelector(self.eipconfig, -3)
        gateways = gateway_selector.get_gateways()
        self.assertEqual(gateways, [u'3.4.5.6', u'2.3.4.5', u'1.2.3.4'])

    def test_correct_order_gmt_minus_7(self):
        gateway_selector = VPNGatewaySelector(self.eipconfig, -7)
        gateways = gateway_selector.get_gateways()
        self.assertEqual(gateways, [u'2.3.4.5', u'3.4.5.6', u'1.2.3.4'])

    def test_correct_order_gmt_plus_5(self):
        gateway_selector = VPNGatewaySelector(self.eipconfig, 5)
        gateways = gateway_selector.get_gateways()
        self.assertEqual(gateways, [u'1.2.3.4', u'3.4.5.6', u'2.3.4.5'])

    def test_correct_order_gmt_plus_10(self):
        gateway_selector = VPNGatewaySelector(self.eipconfig, 10)
        gateways = gateway_selector.get_gateways()
        self.assertEqual(gateways, [u'2.3.4.5', u'1.2.3.4', u'3.4.5.6'])


if __name__ == "__main__":
    unittest.main()
