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

from pixelated.resources import respond_json
import os
from twisted.web.resource import Resource

from pixelated.resources.logout_resource import LogoutResource


class FeaturesResource(Resource):
    DISABLED_FEATURES = ['draftReply']
    isLeaf = True

    def __init__(self, multi_user=False):
        Resource.__init__(self)
        self._multi_user = multi_user

    def render_GET(self, request):
        dispatcher_features = self._dispatcher_features()
        disabled_features = self._disabled_features()
        return respond_json(
            {'disabled_features': disabled_features, 'dispatcher_features': dispatcher_features}, request)

    def _dispatcher_features(self):
        dispatcher_features = {}
        if os.environ.get('DISPATCHER_LOGOUT_URL'):
            dispatcher_features['logout'] = os.environ.get(
                'DISPATCHER_LOGOUT_URL')
        if self._multi_user:
            dispatcher_features['logout'] = '/%s' % LogoutResource.BASE_URL
        return dispatcher_features

    def _disabled_features(self):
        disabled_features = [
            default_disabled_feature for default_disabled_feature in self.DISABLED_FEATURES]
        if os.environ.get('FEEDBACK_URL') is None:
            disabled_features.append('feedback')
        return disabled_features
