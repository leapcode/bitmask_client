from u1db import errors
from u1db.remote.http_target import HTTPSyncTarget
from couchdb import *
from soledad.backends.objectstore import ObjectStore


class CouchDatabase(ObjectStore):
    """A U1DB implementation that uses Couch as its persistence layer."""

    def __init__(self, url, database, full_commit=True, session=None): 
        """Create a new Couch data container."""
        self._url = url
        self._full_commit = full_commit
        self._session = session
        self._server = couchdb.Server(url=self._url,
                                      full_commit=self._full_commit,
                                      session=self._session)
        # this will ensure that transaction and sync logs exist and are
        # up-to-date.
        super(CouchDatabase, self)
        self._database = self._server[database]

    #-------------------------------------------------------------------------
    # implemented methods from Database
    #-------------------------------------------------------------------------

    def _get_doc(self, doc_id, check_for_conflicts=False):
        """Get just the document content, without fancy handling.
        
        Conflicts do not happen on server side, so there's no need to check
        for them.
        """
        cdoc = self._database.get(doc_id)
        if cdoc is not None:
            content = {}
            for key, value in content:
                if not key in ['_id', '_rev', '_u1db_rev']:
                    content[key] = value
            doc = self._factory(doc_id=doc_id, rev=cdoc['_u1db_rev'])
            doc.content = content
        return doc

    def get_all_docs(self, include_deleted=False):
        """Get all documents from the database."""
        generation = self._get_generation()
        results = []
        for doc_id in self._database:
            doc = self._get_doc(doc_id)
            if doc.content is None and not include_deleted:
                continue
            results.append(doc)
        return (generation, results)

    def _put_doc(self, doc, new_rev):
        # map u1db metadata to couch
        content = doc.content
        content['_id'] = doc.doc_id
        content['_u1db_rev'] = new_rev
        self._database.save(doc.content)

    def get_sync_target(self):
        return CouchSyncTarget(self)

    def close(self):
        raise NotImplementedError(self.close)

    def sync(self, url, creds=None, autocreate=True):
        from u1db.sync import Synchronizer
        from u1db.remote.http_target import CouchSyncTarget
        return Synchronizer(self, CouchSyncTarget(url, creds=creds)).sync(
            autocreate=autocreate)

    #-------------------------------------------------------------------------
    # Couch specific methods
    #-------------------------------------------------------------------------

    # no specific methods so far.

class CouchSyncTarget(HTTPSyncTarget):

    def get_sync_info(self, source_replica_uid):
        source_gen, source_trans_id = self._db._get_replica_gen_and_trans_id(
            source_replica_uid)
        my_gen, my_trans_id = self._db._get_generation_info()
        return (
            self._db._replica_uid, my_gen, my_trans_id, source_gen,
            source_trans_id)

    def record_sync_info(self, source_replica_uid, source_replica_generation,
                         source_replica_transaction_id):
        if self._trace_hook:
            self._trace_hook('record_sync_info')
        self._db._set_replica_gen_and_trans_id(
            source_replica_uid, source_replica_generation,
            source_replica_transaction_id)


