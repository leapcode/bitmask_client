# Copyright 2011 Canonical Ltd.
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

"""HTTPDatabase to access a remote db over the HTTP API."""

try:
    import simplejson as json
except ImportError:
    import json  # noqa
import uuid

from u1db import (
    Database,
    Document,
    errors,
    )
from u1db.remote import (
    http_client,
    http_errors,
    http_target,
    )


DOCUMENT_DELETED_STATUS = http_errors.wire_description_to_status[
    errors.DOCUMENT_DELETED]


class HTTPDatabase(http_client.HTTPClientBase, Database):
    """Implement the Database API to a remote HTTP server."""

    def __init__(self, url, document_factory=None, creds=None):
        super(HTTPDatabase, self).__init__(url, creds=creds)
        self._factory = document_factory or Document

    def set_document_factory(self, factory):
        self._factory = factory

    @staticmethod
    def open_database(url, create):
        db = HTTPDatabase(url)
        db.open(create)
        return db

    @staticmethod
    def delete_database(url):
        db = HTTPDatabase(url)
        db._delete()
        db.close()

    def open(self, create):
        if create:
            self._ensure()
        else:
            self._check()

    def _check(self):
        return self._request_json('GET', [])[0]

    def _ensure(self):
        self._request_json('PUT', [], {}, {})

    def _delete(self):
        self._request_json('DELETE', [], {}, {})

    def put_doc(self, doc):
        if doc.doc_id is None:
            raise errors.InvalidDocId()
        params = {}
        if doc.rev is not None:
            params['old_rev'] = doc.rev
        res, headers = self._request_json('PUT', ['doc', doc.doc_id], params,
                                          doc.get_json(), 'application/json')
        doc.rev = res['rev']
        return res['rev']

    def get_doc(self, doc_id, include_deleted=False):
        try:
            res, headers = self._request(
                'GET', ['doc', doc_id], {"include_deleted": include_deleted})
        except errors.DocumentDoesNotExist:
            return None
        except errors.HTTPError, e:
            if (e.status == DOCUMENT_DELETED_STATUS and
                'x-u1db-rev' in e.headers):
                res = None
                headers = e.headers
            else:
                raise
        doc_rev = headers['x-u1db-rev']
        has_conflicts = json.loads(headers['x-u1db-has-conflicts'])
        doc = self._factory(doc_id, doc_rev, res)
        doc.has_conflicts = has_conflicts
        return doc

    def get_docs(self, doc_ids, check_for_conflicts=True,
                 include_deleted=False):
        if not doc_ids:
            return
        doc_ids = ','.join(doc_ids)
        res, headers = self._request(
            'GET', ['docs'], {
                "doc_ids": doc_ids, "include_deleted": include_deleted,
                "check_for_conflicts": check_for_conflicts})
        for doc_dict in json.loads(res):
            doc = self._factory(
                doc_dict['doc_id'], doc_dict['doc_rev'], doc_dict['content'])
            doc.has_conflicts = doc_dict['has_conflicts']
            yield doc

    def create_doc_from_json(self, content, doc_id=None):
        if doc_id is None:
            doc_id = 'D-%s' % (uuid.uuid4().hex,)
        res, headers = self._request_json('PUT', ['doc', doc_id], {},
                                          content, 'application/json')
        new_doc = self._factory(doc_id, res['rev'], content)
        return new_doc

    def delete_doc(self, doc):
        if doc.doc_id is None:
            raise errors.InvalidDocId()
        params = {'old_rev': doc.rev}
        res, headers = self._request_json('DELETE',
            ['doc', doc.doc_id], params)
        doc.make_tombstone()
        doc.rev = res['rev']

    def get_sync_target(self):
        st = http_target.HTTPSyncTarget(self._url.geturl())
        st._creds = self._creds
        return st
