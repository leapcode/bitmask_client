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

import requests


if requests.__version__ == '2.0.0':
    try:
        import requests.packages.urllib3.connectionpool
        from socket import error as SocketError, timeout as SocketTimeout
        from requests.packages.urllib3.packages.ssl_match_hostname import CertificateError, match_hostname
        import socket
        import ssl

        from requests.packages.urllib3.exceptions import (
            ClosedPoolError,
            ConnectTimeoutError,
            EmptyPoolError,
            HostChangedError,
            MaxRetryError,
            SSLError,
            ReadTimeoutError,
            ProxyError,
        )

        from requests.packages.urllib3.util import (
            assert_fingerprint,
            get_host,
            is_connection_dropped,
            resolve_cert_reqs,
            resolve_ssl_version,
            ssl_wrap_socket,
            Timeout,
        )

        def patched_connect(self):
            # Add certificate verification
            try:
                sock = socket.create_connection(
                    address=(self.host, self.port), timeout=self.timeout)
            except SocketTimeout:
                raise ConnectTimeoutError(
                    self, "Connection to %s timed out. (connect timeout=%s)" % (self.host, self.timeout))

            resolved_cert_reqs = resolve_cert_reqs(self.cert_reqs)
            resolved_ssl_version = resolve_ssl_version(self.ssl_version)

            if self._tunnel_host:
                self.sock = sock
                # Calls self._set_hostport(), so self.host is
                # self._tunnel_host below.
                self._tunnel()

            # Wrap socket using verification with the root certs in
            # trusted_root_certs
            self.sock = ssl_wrap_socket(sock, self.key_file, self.cert_file,
                                        cert_reqs=resolved_cert_reqs,
                                        ca_certs=self.ca_certs,
                                        server_hostname=self.host,
                                        ssl_version=resolved_ssl_version)

            if self.assert_fingerprint:
                assert_fingerprint(self.sock.getpeercert(binary_form=True),
                                   self.assert_fingerprint)
            elif resolved_cert_reqs != ssl.CERT_NONE and self.assert_hostname is not False:
                match_hostname(self.sock.getpeercert(),
                               self.assert_hostname or self.host)

        requests.packages.urllib3.connectionpool.VerifiedHTTPSConnection.connect = patched_connect
    except ImportError:
        pass    # The patch is specific for the debian package. Ignore it if it can't be found
