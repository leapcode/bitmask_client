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

import zmq.auth

from leap.bitmask.util import get_path_prefix
from leap.common.files import mkdir_p

KEYS_DIR = os.path.join(get_path_prefix(), 'leap', 'zmq_certificates')


def generate_certificates():
    """
    Generate client and server CURVE certificate files.
    """
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
    frontend_secret_file = os.path.join(KEYS_DIR, "frontend.key_secret")
    public, secret = zmq.auth.load_certificate(frontend_secret_file)
    return public, secret


def get_backend_certificates(base_dir='.'):
    """
    Return the backend's public and secret certificates.
    """
    backend_secret_file = os.path.join(KEYS_DIR, "backend.key_secret")
    public, secret = zmq.auth.load_certificate(backend_secret_file)
    return public, secret
