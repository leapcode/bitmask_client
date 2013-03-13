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

import os
import time
import logging

from OpenSSL import crypto
from dateutil.parser import parse as dateparse

from leap.util.check import leap_assert

logger = logging.getLogger(__name__)


def get_cert_from_string(string):
    """
    Returns the x509 from the contents of this string

    @param string: certificate contents as downloaded
    @type string: str

    @return: x509 or None
    """
    leap_assert(string, "We need something to load")

    x509 = None
    try:
        x509 = crypto.load_certificate(crypto.FILETYPE_PEM, string)
    except Exception as e:
        logger.error("Something went wrong while loading the certificate: %r"
                     % (e,))
    return x509


def get_privatekey_from_string(string):
    """
    Returns the private key from the contents of this string

    @param string: private key contents as downloaded
    @type string: str

    @return: private key or None
    """
    leap_assert(string, "We need something to load")

    pkey = None
    try:
        pkey = crypto.load_privatekey(crypto.FILETYPE_PEM, string)
    except Exception as e:
        logger.error("Something went wrong while loading the certificate: %r"
                     % (e,))
    return pkey


def get_digest(cert_data, method):
    """
    Returns the digest for the cert_data using the method specified

    @param cert_data: certificate data in string form
    @type cert_data: str
    @param method: method to be used for digest
    @type method: str

    @rtype: str
    """
    x509 = get_cert_from_string(cert_data)
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
        cert = get_cert_from_string(string)
        key = get_privatekey_from_string(string)

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


def get_cert_time_boundaries(certfile):
    """
    Returns the time boundaries for the certificate saved in certfile

    @param certfile: path to certificate
    @type certfile: str

    @rtype: tuple (from, to)
    """
    cert = get_cert_from_string(certfile)
    leap_assert(cert, 'There was a problem loading the certificate')

    fromts, tots = (cert.get_notBefore(), cert.get_notAfter())
    from_, to_ = map(
        lambda ts: time.gmtime(time.mktime(dateparse(ts).timetuple())),
        (fromts, tots))
    return from_, to_


def should_redownload(certfile, now=time.gmtime):
    """
    Returns True if any of the checks don't pass, False otherwise

    @param certfile: path to certificate
    @type certfile: str
    @param now: current date function, ONLY USED FOR TESTING

    @rtype: bool
    """
    exists = os.path.isfile(certfile)

    if not exists:
        return True

    certdata = None
    try:
        with open(certfile, "r") as f:
            certdata = f.read()
            if not is_valid_pemfile(certdata):
                return True
    except:
        return True

    valid_from, valid_to = get_cert_time_boundaries(certdata)

    if not (valid_from < now() < valid_to):
        return True

    return False
