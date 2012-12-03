# License?

"""A U1DB implementation that uses OpenStack Swift as its persistence layer."""

try:
    import simplejson as json
except ImportError:
    import json  # noqa

from u1db.backends import CommonBackend, CommonSyncTarget
from u1db import (
    Document,
    errors,
    query_parser,
    vectorclock,
    )
from u1db.remote.http_target import HTTPSyncTarget

from swiftclient import client
import base64


class OpenStackDatabase(CommonBackend):
    """A U1DB implementation that uses OpenStack as its persistence layer."""

    def __init__(self, auth_url, user, auth_key):
        """Create a new OpenStack data container."""
        self._auth_url = auth_url
        self._user = user
        self._auth_key = auth_key
        self.set_document_factory(LeapDocument)
        self._connection = swiftclient.Connection(self._auth_url, self._user,
                                                  self._auth_key)

    #-------------------------------------------------------------------------
    # implemented methods from Database
    #-------------------------------------------------------------------------

    def set_document_factory(self, factory):
        self._factory = factory

    def set_document_size_limit(self, limit):
        raise NotImplementedError(self.set_document_size_limit)

    def whats_changed(self, old_generation=0):
        raise NotImplementedError(self.whats_changed)

    def get_doc(self, doc_id, include_deleted=False):
        raise NotImplementedError(self.get_doc)

    def get_all_docs(self, include_deleted=False):
        """Get all documents from the database."""
        raise NotImplementedError(self.get_all_docs)

    def put_doc(self, doc):
        raise NotImplementedError(self.put_doc)

    def delete_doc(self, doc):
        raise NotImplementedError(self.delete_doc)

    # start of index-related methods: these are not supported by this backend.

    def create_index(self, index_name, *index_expressions):
        return False

    def delete_index(self, index_name):
        return False

    def list_indexes(self):
        return []

    def get_from_index(self, index_name, *key_values):
        return []

    def get_range_from_index(self, index_name, start_value=None,
                             end_value=None):
        return []

    def get_index_keys(self, index_name):
        return []

    # end of index-related methods: these are not supported by this backend.

    def get_doc_conflicts(self, doc_id):
        return []

    def resolve_doc(self, doc, conflicted_doc_revs):
        raise NotImplementedError(self.resolve_doc)

    def get_sync_target(self):
        return OpenStackSyncTarget(self)

    def close(self):
        raise NotImplementedError(self.close)

    def sync(self, url, creds=None, autocreate=True):
        raise NotImplementedError(self.close)

    def _get_replica_gen_and_trans_id(self, other_replica_uid):
        raise NotImplementedError(self._get_replica_gen_and_trans_id)

    def _set_replica_gen_and_trans_id(self, other_replica_uid,
                                      other_generation, other_transaction_id):
        raise NotImplementedError(self._set_replica_gen_and_trans_id)

    #-------------------------------------------------------------------------
    # implemented methods from CommonBackend
    #-------------------------------------------------------------------------

    def _get_generation(self):
        raise NotImplementedError(self._get_generation)

    def _get_generation_info(self):
        raise NotImplementedError(self._get_generation_info)

    def _get_doc(self, doc_id, check_for_conflicts=False):
        """Get just the document content, without fancy handling."""
        raise NotImplementedError(self._get_doc)

    def _has_conflicts(self, doc_id):
        raise NotImplementedError(self._has_conflicts)

    def _get_transaction_log(self):
        raise NotImplementedError(self._get_transaction_log)

    def _put_and_update_indexes(self, doc_id, old_doc, new_rev, content):
        raise NotImplementedError(self._put_and_update_indexes)


    def _get_trans_id_for_gen(self, generation):
        raise NotImplementedError(self._get_trans_id_for_gen)

    #-------------------------------------------------------------------------
    # OpenStack specific methods
    #-------------------------------------------------------------------------

    def _is_initialized(self, c):
        raise NotImplementedError(self._is_initialized)

    def _initialize(self, c):
        raise NotImplementedError(self._initialize)

    def _get_auth(self):
        self._url, self._auth_token = self._connection.get_auth(self._auth_url,
                                                                self._user,
                                                                self._auth_key)
        return self._url, self.auth_token


class LeapDocument(Document):

    def __init__(self, doc_id=None, rev=None, json='{}', has_conflicts=False,
                 encrypted_json=None):
        super(Document, self).__init__(doc_id, rev, json, has_conflicts)
        if encrypted_json:
            self.set_encrypted_json(encrypted_json)

    def get_encrypted_json(self):
        """
        Returns document's json serialization encrypted with user's public key.
        """
        # TODO: replace for openpgp encryption with users's pub key.
        return base64.b64encode(self.get_json())

    def set_encrypted_json(self):
        """
        Set document's content based on encrypted version of json string.
        """
        # TODO:
        #   - replace for openpgp decryption using user's priv key.
        #   - raise error if unsuccessful.
        return self.set_json(base64.b64decode(self.get_json()))


class LeapSyncTarget(HTTPSyncTarget):

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
                doc = LeapDocument(entry['id'], entry['rev'],
                                   encrypted_json=entry['content'])
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
            size += prepare(id=doc.doc_id, rev=doc.rev,
                            content=doc.get_encrypted_json(),
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


class OpenStackSyncTarget(CommonSyncTarget):

    def get_sync_info(self, source_replica_uid):
        raise NotImplementedError(self.get_sync_info)

    def record_sync_info(self, source_replica_uid, source_replica_generation,
                         source_replica_transaction_id):
        raise NotImplementedError(self.record_sync_info)
