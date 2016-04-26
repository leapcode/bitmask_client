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
import base64
from twisted.internet import defer
import os


class SearchIndexStorageKey(object):
    __slots__ = '_soledad'

    def __init__(self, soledad):
        self._soledad = soledad

    @defer.inlineCallbacks
    def get_or_create_key(self):
        docs = yield self._soledad.get_from_index('by-type', 'index_key')

        if len(docs):
            key = docs[0].content['value']
        else:
            key = self._new_index_key()
            yield self._store_key_in_soledad(key)
        defer.returnValue(key)

    def _new_index_key(self):
        return os.urandom(64)  # 32 for encryption, 32 for hmac

    def _store_key_in_soledad(self, index_key):
        return self._soledad.create_doc(dict(type='index_key', value=base64.encodestring(index_key)))
