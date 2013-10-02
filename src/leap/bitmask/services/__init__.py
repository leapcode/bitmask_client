# -*- coding: utf-8 -*-
# __init__.py
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
Services module.
"""
import logging
import os

from PySide import QtCore

from leap.bitmask.config import flags
from leap.bitmask.crypto.srpauth import SRPAuth
from leap.bitmask.util.constants import REQUEST_TIMEOUT
from leap.bitmask.util.privilege_policies import is_missing_policy_permissions
from leap.bitmask.util.request_helpers import get_content
from leap.bitmask import util

from leap.common.check import leap_assert
from leap.common.config.baseconfig import BaseConfig
from leap.common.files import get_mtime

logger = logging.getLogger(__name__)


DEPLOYED = ["openvpn", "mx"]


def get_service_display_name(service):
    """
    Returns the name to display of the given service.
    If there is no configured name for that service, then returns the same
    parameter

    :param service: the 'machine' service name
    :type service: str

    :rtype: str
    """
    # qt translator method helper
    _tr = QtCore.QObject().tr

    # Correspondence for services and their name to display
    EIP_LABEL = _tr("Encrypted Internet")
    MX_LABEL = _tr("Encrypted Mail")

    service_display = {
        "openvpn": EIP_LABEL,
        "mx": MX_LABEL
    }

    # If we need to add a warning about eip needing
    # administrative permissions to start. That can be either
    # because we are running in standalone mode, or because we could
    # not find the needed privilege escalation mechanisms being operative.
    if flags.STANDALONE or is_missing_policy_permissions():
        EIP_LABEL += " " + _tr("(will need admin password to start)")

    return service_display.get(service, service)


def get_supported(services):
    """
    Returns a list of the available services.

    :param services: a list containing the services to be filtered.
    :type services: list of str

    :returns: a list of the available services
    :rtype: list of str
    """
    return filter(lambda s: s in DEPLOYED, services)


def download_service_config(provider_config, service_config,
                            session,
                            download_if_needed=True):
    """
    Downloads config for a given service.

    :param provider_config: an instance of ProviderConfig
    :type provider_config: ProviderConfig

    :param service_config: an instance of a particular Service config.
    :type service_config: BaseConfig

    :param session: an instance of a fetcher.session
                    (currently we're using requests only, but it can be
                    anything that implements that interface)
    :type session: requests.sessions.Session
    """
    service_name = service_config.name
    service_json = "{0}-service.json".format(service_name)
    headers = {}
    mtime = get_mtime(os.path.join(util.get_path_prefix(),
                                   "leap", "providers",
                                   provider_config.get_domain(),
                                   service_json))

    if download_if_needed and mtime:
        headers['if-modified-since'] = mtime

    api_version = provider_config.get_api_version()

    config_uri = "%s/%s/config/%s-service.json" % (
        provider_config.get_api_uri(),
        api_version,
        service_name)
    logger.debug('Downloading %s config from: %s' % (
        service_name.upper(),
        config_uri))

    # XXX make and use @with_srp_auth decorator
    srp_auth = SRPAuth(provider_config)
    session_id = srp_auth.get_session_id()
    cookies = None
    if session_id:
        cookies = {"_session_id": session_id}

    res = session.get(config_uri,
                      verify=provider_config.get_ca_cert_path(),
                      headers=headers,
                      timeout=REQUEST_TIMEOUT,
                      cookies=cookies)
    res.raise_for_status()

    service_config.set_api_version(api_version)

    # Not modified
    service_path = ("leap", "providers", provider_config.get_domain(),
                    service_json)
    if res.status_code == 304:
        logger.debug(
            "{0} definition has not been modified".format(
                service_name.upper()))
        service_config.load(os.path.join(*service_path))
    else:
        service_definition, mtime = get_content(res)
        service_config.load(data=service_definition, mtime=mtime)
        service_config.save(service_path)


class ServiceConfig(BaseConfig):
    """
    Base class used by the different service configs
    """

    _service_name = None

    @property
    def name(self):
        """
        Getter for the service name.
        Derived classes should assign it.
        """
        leap_assert(self._service_name is not None)
        return self._service_name
