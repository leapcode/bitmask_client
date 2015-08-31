# -*- coding: utf-8 -*-
# pinned.py
# Copyright (C) 2013-2014 LEAP
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
Pinned Providers
"""
from leap.bitmask.logs.utils import get_logger
from leap.bitmask.provider import pinned_calyx
from leap.bitmask.provider import pinned_demobitmask
from leap.bitmask.provider import pinned_riseup

logger = get_logger()


class PinnedProviders(object):
    """
    Represents the providers that are pinned in Bitmask
    """

    CONFIG_KEY = "config"
    CACERT_KEY = "cacert"
    PREFERRED_PROVIDER = pinned_demobitmask.DOMAIN

    PROVIDERS = {
        pinned_calyx.DOMAIN: {
            CONFIG_KEY: pinned_calyx.PROVIDER_JSON,
            CACERT_KEY: pinned_calyx.CACERT_PEM,
        },
        pinned_demobitmask.DOMAIN: {
            CONFIG_KEY: pinned_demobitmask.PROVIDER_JSON,
            CACERT_KEY: pinned_demobitmask.CACERT_PEM,
        },
        pinned_riseup.DOMAIN: {
            CONFIG_KEY: pinned_riseup.PROVIDER_JSON,
            CACERT_KEY: pinned_riseup.CACERT_PEM,
        }
    }

    def __init__(self):
        pass

    @classmethod
    def domains(self):
        """
        Return the domains that are pinned in here.
        The first domain in the list is the preferred one.

        :rtype: list of str
        """
        domains = self.PROVIDERS.keys()
        domains.remove(self.PREFERRED_PROVIDER)
        domains.insert(0, self.PREFERRED_PROVIDER)

        return domains

    @classmethod
    def save_hardcoded(self, domain, provider_path, cacert_path):
        """
        Save the pinned content for provider.json and cacert.pem to
        the specified paths

        :param domain: domain of the pinned provider
        :type domain: str
        :param provider_path: path where the pinned provider.json will
                              be saved
        :type provider_path: str
        :param cacert_path: path where the pinned cacert.pem will be
                            saved
        :type cacert_path: str
        """
        with open(provider_path, "w") as f:
            f.write(self.PROVIDERS[domain][self.CONFIG_KEY])

        with open(cacert_path, "w") as f:
            f.write(self.PROVIDERS[domain][self.CACERT_KEY])
