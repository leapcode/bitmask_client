# Copyright 2011-2012 Canonical Ltd.
#
# This file is part of u1db.
#
# u1db is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# u1db is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with u1db.  If not, see <http://www.gnu.org/licenses/>.

"""Base class to make requests to a remote HTTP server."""

import httplib
from oauth import oauth
try:
    import simplejson as json
except ImportError:
    import json  # noqa
import socket
import ssl
import sys
import urlparse
import urllib

from time import sleep
from u1db import (
    errors,
    )
from u1db.remote import (
    http_errors,
    )

from u1db.remote.ssl_match_hostname import (  # noqa
    CertificateError,
    match_hostname,
    )

# Ubuntu/debian
# XXX other...
CA_CERTS = "/etc/ssl/certs/ca-certificates.crt"


def _encode_query_parameter(value):
    """Encode query parameter."""
    if isinstance(value, bool):
        if value:
            value = 'true'
        else:
            value = 'false'
    return unicode(value).encode('utf-8')


class _VerifiedHTTPSConnection(httplib.HTTPSConnection):
    """HTTPSConnection verifying server side certificates."""
    # derived from httplib.py

    def connect(self):
        "Connect to a host on a given (SSL) port."

        sock = socket.create_connection((self.host, self.port),
                                        self.timeout, self.source_address)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        if sys.platform.startswith('linux'):
            cert_opts = {
                'cert_reqs': ssl.CERT_REQUIRED,
                'ca_certs': CA_CERTS
                }
        else:
            # XXX no cert verification implemented elsewhere for now
            cert_opts = {}
        self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
                                    ssl_version=ssl.PROTOCOL_SSLv3,
                                    **cert_opts
                                    )
        if cert_opts:
            match_hostname(self.sock.getpeercert(), self.host)


class HTTPClientBase(object):
    """Base class to make requests to a remote HTTP server."""

    # by default use HMAC-SHA1 OAuth signature method to not disclose
    # tokens
    # NB: given that the content bodies are not covered by the
    # signatures though, to achieve security (against man-in-the-middle
    # attacks for example) one would need HTTPS
    oauth_signature_method = oauth.OAuthSignatureMethod_HMAC_SHA1()

    # Will use these delays to retry on 503 befor finally giving up. The final
    # 0 is there to not wait after the final try fails.
    _delays = (1, 1, 2, 4, 0)

    def __init__(self, url, creds=None):
        self._url = urlparse.urlsplit(url)
        self._conn = None
        self._creds = {}
        if creds is not None:
            if len(creds) != 1:
                raise errors.UnknownAuthMethod()
            auth_meth, credentials = creds.items()[0]
            try:
                set_creds = getattr(self, 'set_%s_credentials' % auth_meth)
            except AttributeError:
                raise errors.UnknownAuthMethod(auth_meth)
            set_creds(**credentials)

    def set_oauth_credentials(self, consumer_key, consumer_secret,
                              token_key, token_secret):
        self._creds = {'oauth': (
            oauth.OAuthConsumer(consumer_key, consumer_secret),
            oauth.OAuthToken(token_key, token_secret))}

    def _ensure_connection(self):
        if self._conn is not None:
            return
        if self._url.scheme == 'https':
            connClass = _VerifiedHTTPSConnection
        else:
            connClass = httplib.HTTPConnection
        self._conn = connClass(self._url.hostname, self._url.port)

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    # xxx retry mechanism?

    def _error(self, respdic):
        descr = respdic.get("error")
        exc_cls = errors.wire_description_to_exc.get(descr)
        if exc_cls is not None:
            message = respdic.get("message")
            raise exc_cls(message)

    def _response(self):
        resp = self._conn.getresponse()
        body = resp.read()
        headers = dict(resp.getheaders())
        if resp.status in (200, 201):
            return body, headers
        elif resp.status in http_errors.ERROR_STATUSES:
            try:
                respdic = json.loads(body)
            except ValueError:
                pass
            else:
                self._error(respdic)
        # special case
        if resp.status == 503:
            raise errors.Unavailable(body, headers)
        raise errors.HTTPError(resp.status, body, headers)

    def _sign_request(self, method, url_query, params):
        if 'oauth' in self._creds:
            consumer, token = self._creds['oauth']
            full_url = "%s://%s%s" % (self._url.scheme, self._url.netloc,
                                      url_query)
            oauth_req = oauth.OAuthRequest.from_consumer_and_token(
                consumer, token,
                http_method=method,
                parameters=params,
                http_url=full_url
                )
            oauth_req.sign_request(
                self.oauth_signature_method, consumer, token)
            # Authorization: OAuth ...
            return oauth_req.to_header().items()
        else:
            return []

    def _request(self, method, url_parts, params=None, body=None,
                                                       content_type=None):
        self._ensure_connection()
        unquoted_url = url_query = self._url.path
        if url_parts:
            if not url_query.endswith('/'):
                url_query += '/'
                unquoted_url = url_query
            url_query += '/'.join(urllib.quote(part, safe='')
                                  for part in url_parts)
            # oauth performs its own quoting
            unquoted_url += '/'.join(url_parts)
        encoded_params = {}
        if params:
            for key, value in params.items():
                key = unicode(key).encode('utf-8')
                encoded_params[key] = _encode_query_parameter(value)
            url_query += ('?' + urllib.urlencode(encoded_params))
        if body is not None and not isinstance(body, basestring):
            body = json.dumps(body)
            content_type = 'application/json'
        headers = {}
        if content_type:
            headers['content-type'] = content_type
        headers.update(
            self._sign_request(method, unquoted_url, encoded_params))
        for delay in self._delays:
            try:
                self._conn.request(method, url_query, body, headers)
                return self._response()
            except errors.Unavailable, e:
                sleep(delay)
        raise e

    def _request_json(self, method, url_parts, params=None, body=None,
                                                            content_type=None):
        res, headers = self._request(method, url_parts, params, body,
                                     content_type)
        return json.loads(res), headers
