# -*- coding: utf-8 -*-
# eipconfig.py
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
Provider configuration
"""
import os
import logging

from leap.common.check import leap_assert, leap_assert_type
from leap.common.config.baseconfig import BaseConfig
from leap.config.providerconfig import ProviderConfig
from leap.services.eip.eipspec import eipservice_config_spec

logger = logging.getLogger(__name__)


class EIPConfig(BaseConfig):
    """
    Provider configuration abstraction class
    """

    def __init__(self):
        BaseConfig.__init__(self)

    def _get_spec(self):
        """
        Returns the spec object for the specific configuration
        """
        return eipservice_config_spec

    def get_clusters(self):
        # TODO: create an abstraction for clusters
        return self._safe_get_value("clusters")

    def get_gateways(self):
        # TODO: create an abstraction for gateways
        return self._safe_get_value("gateways")

    def get_openvpn_configuration(self):
        return self._safe_get_value("openvpn_configuration")

    def get_serial(self):
        return self._safe_get_value("serial")

    def get_version(self):
        return self._safe_get_value("version")

    def get_gateway_ip(self, index=0):
        gateways = self.get_gateways()
        leap_assert(len(gateways) > 0, "We don't have any gateway!")
        if index > len(gateways):
            index = 0
            logger.warning("Provided an unknown gateway index %s, " +
                           "defaulting to 0")
        return gateways[0]["ip_address"]

    def get_client_cert_path(self,
                             providerconfig=None,
                             about_to_download=False):
        """
        Returns the path to the certificate used by openvpn
        """

        leap_assert(providerconfig, "We need a provider")
        leap_assert_type(providerconfig, ProviderConfig)

        cert_path = os.path.join(self.get_path_prefix(),
                                 "leap",
                                 "providers",
                                 providerconfig.get_domain(),
                                 "keys",
                                 "client",
                                 "openvpn.pem")

        if not about_to_download:
            leap_assert(os.path.exists(cert_path),
                        "You need to download the certificate first")
            logger.debug("Using OpenVPN cert %s" % (cert_path,))

        return cert_path


if __name__ == "__main__":
    logger = logging.getLogger(name='leap')
    logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s '
        '- %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)

    eipconfig = EIPConfig()

    try:
        eipconfig.get_clusters()
    except Exception as e:
        assert isinstance(e, AssertionError), "Expected an assert"
        print "Safe value getting is working"

    if eipconfig.load("leap/providers/bitmask.net/eip-service.json"):
        print eipconfig.get_clusters()
        print eipconfig.get_gateways()
        print eipconfig.get_openvpn_configuration()
        print eipconfig.get_serial()
        print eipconfig.get_version()
