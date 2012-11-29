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

"""SyncTarget API implementation to a remote HTTP server."""

try:
    import simplejson as json
except ImportError:
    import json  # noqa

from u1db import (
    Document,
    SyncTarget,
    )
from u1db.errors import (
    BrokenSyncStream,
    )
from u1db.remote import (
    http_client,
    utils,
    )


class HTTPSyncTarget(http_client.HTTPClientBase, SyncTarget):
    """Implement the SyncTarget api to a remote HTTP server."""

    @staticmethod
    def connect(url):
        return HTTPSyncTarget(url)

    def get_sync_info(self, source_replica_uid):
        self._ensure_connection()
        res, _ = self._request_json('GET', ['sync-from', source_replica_uid])
        return (res['target_replica_uid'], res['target_replica_generation'],
                res['target_replica_transaction_id'],
                res['source_replica_generation'], res['source_transaction_id'])

    def record_sync_info(self, source_replica_uid, source_replica_generation,
                         source_transaction_id):
        self._ensure_connection()
        if self._trace_hook:  # for tests
            self._trace_hook('record_sync_info')
        self._request_json('PUT', ['sync-from', source_replica_uid], {},
                              {'generation': source_replica_generation,
                               'transaction_id': source_transaction_id})

    def _parse_sync_stream(self, data, return_doc_cb, ensure_callback=None):
        parts = data.splitlines()  # one at a time
        if not parts or parts[0] != '[':
            raise BrokenSyncStream
        data = parts[1:-1]
        comma = False
        if data:
            line, comma = utils.check_and_strip_comma(data[0])
            res = json.loads(line)
            if ensure_callback and 'replica_uid' in res:
                ensure_callback(res['replica_uid'])
            for entry in data[1:]:
                if not comma:  # missing in between comma
                    raise BrokenSyncStream
                line, comma = utils.check_and_strip_comma(entry)
                entry = json.loads(line)
                doc = Document(entry['id'], entry['rev'], entry['content'])
                return_doc_cb(doc, entry['gen'], entry['trans_id'])
        if parts[-1] != ']':
            try:
                partdic = json.loads(parts[-1])
            except ValueError:
                pass
            else:
                if isinstance(partdic, dict):
                    self._error(partdic)
            raise BrokenSyncStream
        if not data or comma:  # no entries or bad extra comma
            raise BrokenSyncStream
        return res

    def sync_exchange(self, docs_by_generations, source_replica_uid,
                      last_known_generation, last_known_trans_id,
                      return_doc_cb, ensure_callback=None):
        self._ensure_connection()
        if self._trace_hook:  # for tests
            self._trace_hook('sync_exchange')
        url = '%s/sync-from/%s' % (self._url.path, source_replica_uid)
        self._conn.putrequest('POST', url)
        self._conn.putheader('content-type', 'application/x-u1db-sync-stream')
        for header_name, header_value in self._sign_request('POST', url, {}):
            self._conn.putheader(header_name, header_value)
        entries = ['[']
        size = 1

        def prepare(**dic):
            entry = comma + '\r\n' + json.dumps(dic)
            entries.append(entry)
            return len(entry)

        comma = ''
        size += prepare(
            last_known_generation=last_known_generation,
            last_known_trans_id=last_known_trans_id,
            ensure=ensure_callback is not None)
        comma = ','
        for doc, gen, trans_id in docs_by_generations:
            size += prepare(id=doc.doc_id, rev=doc.rev, content=doc.get_json(),
                            gen=gen, trans_id=trans_id)
        entries.append('\r\n]')
        size += len(entries[-1])
        self._conn.putheader('content-length', str(size))
        self._conn.endheaders()
        for entry in entries:
            self._conn.send(entry)
        entries = None
        data, _ = self._response()
        res = self._parse_sync_stream(data, return_doc_cb, ensure_callback)
        data = None
        return res['new_generation'], res['new_transaction_id']

    # for tests
    _trace_hook = None

    def _set_trace_hook_shallow(self, cb):
        self._trace_hook = cb
