# Copyright 2012 Canonical Ltd.
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
"""U1DB OAuth authorisation WSGI middleware."""
import httplib
from oauth import oauth
try:
    import simplejson as json
except ImportError:
    import json  # noqa
from urllib import quote
from wsgiref.util import shift_path_info


sign_meth_HMAC_SHA1 = oauth.OAuthSignatureMethod_HMAC_SHA1()
sign_meth_PLAINTEXT = oauth.OAuthSignatureMethod_PLAINTEXT()


class OAuthMiddleware(object):
    """U1DB OAuth Authorisation WSGI middleware."""

    # max seconds the request timestamp is allowed to  be shifted
    # from arrival time
    timestamp_threshold = 300

    def __init__(self, app, base_url, prefix='/~/'):
        self.app = app
        self.base_url = base_url
        self.prefix = prefix

    def get_oauth_data_store(self):
        """Provide a oauth.OAuthDataStore."""
        raise NotImplementedError(self.get_oauth_data_store)

    def _error(self, start_response, status, description, message=None):
        start_response("%d %s" % (status, httplib.responses[status]),
                       [('content-type', 'application/json')])
        err = {"error": description}
        if message:
            err['message'] = message
        return [json.dumps(err)]

    def __call__(self, environ, start_response):
        if self.prefix and not environ['PATH_INFO'].startswith(self.prefix):
            return self._error(start_response, 400, "bad request")
        headers = {}
        if 'HTTP_AUTHORIZATION' in environ:
            headers['Authorization'] = environ['HTTP_AUTHORIZATION']
        oauth_req = oauth.OAuthRequest.from_request(
            http_method=environ['REQUEST_METHOD'],
            http_url=self.base_url + environ['PATH_INFO'],
            headers=headers,
            query_string=environ['QUERY_STRING']
            )
        if oauth_req is None:
            return self._error(start_response, 401, "unauthorized",
                               "Missing OAuth.")
        try:
            self.verify(environ, oauth_req)
        except oauth.OAuthError, e:
            return self._error(start_response, 401, "unauthorized",
                               e.message)
        shift_path_info(environ)
        return self.app(environ, start_response)

    def verify(self, environ, oauth_req):
        """Verify OAuth request, put user_id in the environ."""
        oauth_server = oauth.OAuthServer(self.get_oauth_data_store())
        oauth_server.timestamp_threshold = self.timestamp_threshold
        oauth_server.add_signature_method(sign_meth_HMAC_SHA1)
        oauth_server.add_signature_method(sign_meth_PLAINTEXT)
        consumer, token, parameters = oauth_server.verify_request(oauth_req)
        # filter out oauth bits
        environ['QUERY_STRING'] = '&'.join("%s=%s" % (quote(k, safe=''),
                                                      quote(v, safe=''))
                                           for k, v in parameters.iteritems())
        return consumer, token
