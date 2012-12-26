try:
    import simplejson as json
except ImportError:
    import json  # noqa

from u1db import Document
from u1db.remote.http_target import HTTPSyncTarget
from u1db.remote.http_database import HTTPDatabase
import base64  # unused

#from leap.soledad import util  # import GPGWrapper  # unused


class NoDefaultKey(Exception):
    pass

class NoSoledadInstance(Exception):
    pass


class LeapDocument(Document):
    """
    LEAP Documents are standard u1db documents with cabability of returning an
    encrypted version of the document json string as well as setting document
    content based on an encrypted version of json string.
    """

    def __init__(self, doc_id=None, rev=None, json='{}', has_conflicts=False,
                 encrypted_json=None, soledad=None):
        super(LeapDocument, self).__init__(doc_id, rev, json, has_conflicts)
        self._soledad = soledad
        if encrypted_json:
            self.set_encrypted_json(encrypted_json)

    def get_encrypted_json(self):
        """
        Returns document's json serialization encrypted with user's public key.
        """
        if not self._soledad:
            raise NoSoledadInstance()
        ciphertext = self._soledad.encrypt_symmetric(self.doc_id, self.get_json())
        return json.dumps({'_encrypted_json' : ciphertext})

    def set_encrypted_json(self, encrypted_json):
        """
        Set document's content based on encrypted version of json string.
        """
        if not self._soledad:
            raise NoSoledadInstance()
        ciphertext = json.loads(encrypted_json)['_encrypted_json']
        plaintext = self._soledad.decrypt_symmetric(self.doc_id, ciphertext)
        return self.set_json(plaintext)


class LeapDatabase(HTTPDatabase):
    """Implement the HTTP remote database API to a Leap server."""

    def __init__(self, url, document_factory=None, creds=None, soledad=None):
        super(LeapDatabase, self).__init__(url, creds=creds)
        self._soledad = soledad
        self._factory = LeapDocument

    @staticmethod
    def open_database(url, create):
        db = LeapDatabase(url)
        db.open(create)
        return db

    @staticmethod
    def delete_database(url):
        db = LeapDatabase(url)
        db._delete()
        db.close()

    def get_sync_target(self):
        st = LeapSyncTarget(self._url.geturl())
        st._creds = self._creds
        return st

    def create_doc_from_json(self, content, doc_id=None):
        if doc_id is None:
            doc_id = self._allocate_doc_id()
        res, headers = self._request_json('PUT', ['doc', doc_id], {},
                                          content, 'application/json')
        new_doc = self._factory(doc_id, res['rev'], content, soledad=self._soledad)
        return new_doc


class LeapSyncTarget(HTTPSyncTarget):

    def __init__(self, url, creds=None, soledad=None):
        super(LeapSyncTarget, self).__init__(url, creds)
        self._soledad = soledad

    def _parse_sync_stream(self, data, return_doc_cb, ensure_callback=None):
        """
        Does the same as parent's method but ensures incoming content will be
        decrypted.
        """
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
                # decrypt after receiving from server.
                doc = LeapDocument(entry['id'], entry['rev'],
                                   encrypted_json=entry['content'],
                                   soledad=self._soledad)
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
        """
        Does the same as parent's method but encrypts content before syncing.
        """
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
            # encrypt before sending to server.
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
