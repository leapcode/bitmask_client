# -*- coding: utf-8 -*-
# utils.py
# Copyright (C) 2013, 2014 LEAP
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
Backend utilities to handle ZMQ certificates.
"""
import os
import shutil
import stat

import zmq

try:
    import zmq.auth
except ImportError:
    pass

from leap.bitmask.config import flags
from leap.bitmask.logs.utils import get_logger
from leap.bitmask.util import get_path_prefix
from leap.common.files import mkdir_p
from leap.common.check import leap_assert

logger = get_logger()

KEYS_DIR = os.path.join(get_path_prefix(), 'leap', 'zmq_certificates')


def _zmq_has_curve():
    """
    Return whether the current ZMQ has support for auth and CurveZMQ security.

    :rtype: bool

     Version notes:
       `zmq.curve_keypair()` is new in version 14.0, new in version libzmq-4.0.
            Requires libzmq (>= 4.0) to have been linked with libsodium.
       `zmq.auth` module is new in version 14.1
       `zmq.has()` is new in version 14.1, new in version libzmq-4.1.
    """
    zmq_version = zmq.zmq_version_info()
    pyzmq_version = zmq.pyzmq_version_info()

    if pyzmq_version >= (14, 1, 0) and zmq_version >= (4, 1):
        return zmq.has('curve')

    if pyzmq_version < (14, 1, 0):
        return False

    if zmq_version < (4, 0):
        # security is new in libzmq 4.0
        return False

    try:
        zmq.curve_keypair()
    except zmq.error.ZMQError:
        # security requires libzmq to be linked against libsodium
        return False

    return True


def generate_zmq_certificates():
    """
    Generate client and server CURVE certificate files.
    """
    leap_assert(flags.ZMQ_HAS_CURVE, "CurveZMQ not supported!")

    # Create directory for certificates, remove old content if necessary
    if os.path.exists(KEYS_DIR):
        shutil.rmtree(KEYS_DIR)
    mkdir_p(KEYS_DIR)
    # set permissions to: 0700 (U:rwx G:--- O:---)
    os.chmod(KEYS_DIR, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

    # create new keys in certificates dir
    # public_file, secret_file = create_certificates(...)
    zmq.auth.create_certificates(KEYS_DIR, "frontend")
    zmq.auth.create_certificates(KEYS_DIR, "backend")


def get_frontend_certificates():
    """
    Return the frontend's public and secret certificates.
    """
    leap_assert(flags.ZMQ_HAS_CURVE, "CurveZMQ not supported!")

    frontend_secret_file = os.path.join(KEYS_DIR, "frontend.key_secret")
    public, secret = zmq.auth.load_certificate(frontend_secret_file)
    return public, secret


def get_backend_certificates(base_dir='.'):
    """
    Return the backend's public and secret certificates.
    """
    leap_assert(flags.ZMQ_HAS_CURVE, "CurveZMQ not supported!")

    backend_secret_file = os.path.join(KEYS_DIR, "backend.key_secret")
    public, secret = zmq.auth.load_certificate(backend_secret_file)
    return public, secret


def _certificates_exist():
    """
    Return whether there are certificates in place or not.

    :rtype: bool
    """
    frontend_secret_file = os.path.join(KEYS_DIR, "frontend.key_secret")
    backend_secret_file = os.path.join(KEYS_DIR, "backend.key_secret")
    return os.path.isfile(frontend_secret_file) and \
        os.path.isfile(backend_secret_file)


def generate_zmq_certificates_if_needed():
    """
    Generate the needed ZMQ certificates for backend/frontend communication if
    needed.
    """
    if flags.ZMQ_HAS_CURVE and not _certificates_exist():
        generate_zmq_certificates()


flags.ZMQ_HAS_CURVE = _zmq_has_curve()
