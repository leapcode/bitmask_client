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

import ssl
from requests.adapters import HTTPAdapter
try:
    from urllib3.poolmanager import PoolManager
except:
    from requests.packages.urllib3.poolmanager import PoolManager

VERIFY_HOSTNAME = None


def latest_available_ssl_version():
    try:
        return ssl.PROTOCOL_TLSv1_2
    except AttributeError:
        return ssl.PROTOCOL_TLSv1


class EnforceTLSv1Adapter(HTTPAdapter):
    __slots__ = ('_assert_hostname', '_assert_fingerprint')

    def __init__(self, assert_hostname=VERIFY_HOSTNAME, assert_fingerprint=None):
        self._assert_hostname = assert_hostname
        self._assert_fingerprint = assert_fingerprint
        super(EnforceTLSv1Adapter, self).__init__()

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize,
                                       block=block,
                                       assert_hostname=self._assert_hostname,
                                       assert_fingerprint=self._assert_fingerprint,
                                       cert_reqs=ssl.CERT_REQUIRED)
