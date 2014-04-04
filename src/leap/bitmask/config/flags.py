# -*- coding: utf-8 -*-
# flags.py
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
This file is meant to be used to store global flags that affect the
application.

WARNING: You should NOT use this kind of flags unless you're sure of what
         you're doing, and someone else tells you that you're right.
         Most of the times there is a better and safer alternative.
"""

# The STANDALONE flag is used to:
#   - define a different set of messages for the application when is running
#     inside of a bundle or installed system wide.
#   - use a relative or system wide path to find the configuration files.
#   - search for binaries inside the bundled app instead of the system ones.
#     e.g.: openvpn, gpg
STANDALONE = False

MAIL_LOGFILE = None

# The APP/API version check flags are used to provide a way to skip
# that checks.
# This can be used for:
#   - allow the use of a client that is not compatible with a provider.
#   - use a development version of the client with an older version number
#     since it's not released yet, and it is compatible with a newer provider.
APP_VERSION_CHECK = True
API_VERSION_CHECK = True

# Offline mode?
# Used for skipping soledad bootstrapping/syncs.
OFFLINE = False


# CA cert path
# used to allow self signed certs in requests that needs SSL
CA_CERT_FILE = None
