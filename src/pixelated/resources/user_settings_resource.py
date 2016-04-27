#
# Copyright (c) 2015 ThoughtWorks, Inc.
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

from pixelated.resources import respond_json_deferred, BaseResource
from twisted.web import server

FINGERPRINT_NOT_FOUND = 'Fingerprint not found'


class UserSettingsResource(BaseResource):
    isLeaf = True

    def __init__(self, services_factory):
        BaseResource.__init__(self, services_factory)

    def render_GET(self, request):
        _account_email = self.mail_service(request).account_email

        def finish_request(key):
            _fingerprint = key.fingerprint
            respond_json_deferred(
                {'account_email': _account_email, 'fingerprint': _fingerprint}, request)

        def key_not_found(_):
            respond_json_deferred(
                {'account_email': _account_email, 'fingerprint': FINGERPRINT_NOT_FOUND}, request)

        d = self.keymanager(request).fetch_key(_account_email)
        d.addCallback(finish_request)
        d.addErrback(key_not_found)

        return server.NOT_DONE_YET
