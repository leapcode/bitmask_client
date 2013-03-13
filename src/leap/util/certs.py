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
Implements cert checks and helpers
"""

import logging

from OpenSSL import crypto

from leap.util.check import leap_assert

logger = logging.getLogger(__name__)


def get_digest(cert_data, method):
    """
    Returns the digest for the cert_data using the method specified

    @param cert_data: certificate data in string form
    @type cert_data: str
    @param method: method to be used for digest
    @type method: str

    @rtype: str
    """
    x509 = crypto.load_certificate(crypto.FILETYPE_PEM, cert_data)
    digest = x509.digest(method).replace(":", "").lower()

    return digest


def can_load_cert_and_pkey(string):
    """
    Loads certificate and private key from a buffer, returns True if
    everything went well, False otherwise

    @param string: buffer containing the cert and private key
    @type string: str or any kind of buffer

    @rtype: bool
    """

    can_load = True

    try:
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, string)
        key = crypto.load_privatekey(crypto.FILETYPE_PEM, string)

        leap_assert(cert, 'The certificate could not be loaded')
        leap_assert(key, 'The private key could not be loaded')
    except Exception as e:
        can_load = False
        logger.error("Something went wrong while trying to load "
                     "the certificate: %r" % (e,))

    return can_load


def is_valid_pemfile(cert):
    """
    Checks that the passed string is a valid pem certificate

    @param cert: String containing pem content
    @type cert: str

    @rtype: bool
    """
    leap_assert(cert, "We need a cert to load")

    return can_load_cert_and_pkey(cert)
