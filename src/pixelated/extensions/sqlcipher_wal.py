#
# Copyright (c) 2014 ThoughtWorks, Inc.
#
# Pixelated is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pixelated is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Pixelated. If not, see <http://www.gnu.org/licenses/>.

from sys import platform as _platform

import leap.soledad.client.sqlcipher

# WAL is breaking for the debian sqlcipher package so we need to disable it
# refer to https://leap.se/code/issues/5562
if _platform == 'linux2':
    leap.soledad.client.sqlcipher.SQLCipherDatabase._pragma_write_ahead_logging = lambda x, y: None
