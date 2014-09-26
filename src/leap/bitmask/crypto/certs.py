# -*- coding: utf-8 -*-
# certs.py
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
Utilities for dealing with client certs
"""
import logging
import os

from leap.bitmask.crypto.srpauth import SRPAuth
from leap.bitmask.util.constants import REQUEST_TIMEOUT
from leap.common.files import check_and_fix_urw_only
from leap.common.files import mkdir_p

from leap.common import certs as leap_certs

logger = logging.getLogger(__name__)


def download_client_cert(provider_config, path, session):
    """
    Downloads the client certificate for each service.

    :param provider_config: instance of a ProviderConfig
    :type provider_config: ProviderConfig
    :param path: the path to download the cert to.
    :type path: str
    :param session: a fetcher.session instance. For the moment we only
                   support requests.sessions
    :type session: requests.sessions.Session
    """
    # TODO we should implement the @with_srp_auth decorator
    # again.
    srp_auth = SRPAuth(provider_config)
    session_id = srp_auth.get_session_id()
    token = srp_auth.get_token()
    cookies = None
    if session_id is not None:
        cookies = {"_session_id": session_id}
    cert_uri = "%s/%s/cert" % (
        provider_config.get_api_uri(),
        provider_config.get_api_version())
    logger.debug('getting cert from uri: %s' % cert_uri)

    headers = {}

    # API v2 will only support token auth, but in v1 we can send both
    if token is not None:
        headers["Authorization"] = 'Token token="{0}"'.format(token)

    res = session.get(cert_uri,
                      verify=provider_config
                      .get_ca_cert_path(),
                      cookies=cookies,
                      timeout=REQUEST_TIMEOUT,
                      headers=headers)
    res.raise_for_status()
    client_cert = res.content

    if not leap_certs.is_valid_pemfile(client_cert):
        # XXX raise more specific exception.
        raise Exception("The downloaded certificate is not a "
                        "valid PEM file")

    mkdir_p(os.path.dirname(path))

    try:
        with open(path, "w") as f:
            f.write(client_cert)
    except IOError as exc:
        logger.error(
            "Error saving client cert: %r" % (exc,))
        raise

    check_and_fix_urw_only(path)
