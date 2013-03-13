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

from OpenSSL import crypto


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
