# -*- coding: utf-8 -*-
# providerconfig.py
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
import logging
import os

from leap.common.check import leap_check
from leap.common.config.baseconfig import BaseConfig, LocalizedKey
from leap.config.provider_spec import leap_provider_spec

logger = logging.getLogger(__name__)


class MissingCACert(Exception):
    """
    Raised when a CA certificate is needed but not found.
    """
    pass


class ProviderConfig(BaseConfig):
    """
    Provider configuration abstraction class
    """
    def __init__(self):
        BaseConfig.__init__(self)

    def _get_spec(self):
        """
        Returns the spec object for the specific configuration
        """
        return leap_provider_spec

    def get_api_uri(self):
        return self._safe_get_value("api_uri")

    def get_api_version(self):
        return self._safe_get_value("api_version")

    def get_ca_cert_fingerprint(self):
        return self._safe_get_value("ca_cert_fingerprint")

    def get_ca_cert_uri(self):
        return self._safe_get_value("ca_cert_uri")

    def get_default_language(self):
        return self._safe_get_value("default_language")

    @LocalizedKey
    def get_description(self):
        return self._safe_get_value("description")

    @classmethod
    def sanitize_path_component(cls, component):
        """
        If the provider tries to instrument the component of a path
        that is controlled by them, this will take care of
        removing/escaping all the necessary elements.

        :param component: Path component to process
        :type component: unicode or str

        :returns: The path component properly escaped
        :rtype: unicode or str
        """
        # TODO: Fix for windows, names like "aux" or "con" aren't
        # allowed.
        return component.replace(os.path.sep, "")

    def get_domain(self):
        return ProviderConfig.sanitize_path_component(
            self._safe_get_value("domain"))

    def get_enrollment_policy(self):
        """
        Returns the enrollment policy

        :rtype: string
        """
        return self._safe_get_value("enrollment_policy")

    def get_languages(self):
        return self._safe_get_value("languages")

    @LocalizedKey
    def get_name(self):
        return self._safe_get_value("name")

    def get_services(self):
        """
        Returns a list with the available services in the current provider.

        :rtype: list
        """
        services = self._safe_get_value("services")
        return services

    def get_services_string(self):
        """
        Returns a string with the available services in the current
        provider, ready to be shown to the user.
        """
        services_str = ", ".join(self.get_services())
        services_str = services_str.replace(
            "openvpn", "Encrypted Internet")
        return services_str

    def get_ca_cert_path(self, about_to_download=False):
        """
        Returns the path to the certificate for the current provider.
        It may raise MissingCACert if
        the certificate does not exists and not about_to_download

        :param about_to_download: defines wether we want the path to
                                  download the cert or not. This helps avoid
                                  checking if the cert exists because we
                                  are about to write it.
        :type about_to_download: bool
        """

        cert_path = os.path.join(self.get_path_prefix(),
                                 "leap",
                                 "providers",
                                 self.get_domain(),
                                 "keys",
                                 "ca",
                                 "cacert.pem")

        if not about_to_download:
            cert_exists = os.path.exists(cert_path)
            error_msg = "You need to download the certificate first"
            leap_check(cert_exists, error_msg, MissingCACert)
            logger.debug("Going to verify SSL against %s" % (cert_path,))

        return cert_path

    def provides_eip(self):
        """
        Returns True if this particular provider has the EIP service,
        False otherwise.

        :rtype: bool
        """
        return "openvpn" in self.get_services()

    def provides_mx(self):
        """
        Returns True if this particular provider has the MX service,
        False otherwise.

        :rtype: bool
        """
        return "mx" in self.get_services()


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

    provider = ProviderConfig()

    try:
        provider.get_api_version()
    except Exception as e:
        assert isinstance(e, AssertionError), "Expected an assert"
        print "Safe value getting is working"

    # standalone minitest
    #if provider.load("provider_bad.json"):
    if provider.load("leap/providers/bitmask.net/provider.json"):
        print provider.get_api_version()
        print provider.get_ca_cert_fingerprint()
        print provider.get_ca_cert_uri()
        print provider.get_default_language()
        print provider.get_description()
        print provider.get_description(lang="asd")
        print provider.get_domain()
        print provider.get_enrollment_policy()
        print provider.get_languages()
        print provider.get_name()
        print provider.get_services()
