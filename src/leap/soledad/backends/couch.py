from u1db import errors
from u1db.remote.http_target import HTTPSyncTarget
from couchdb.client import Server, Document
from couchdb.http import ResourceNotFound
from soledad.backends.objectstore import ObjectStore
from soledad.backends.leap import LeapDocument


class CouchDatabase(ObjectStore):
    """A U1DB implementation that uses Couch as its persistence layer."""

    def __init__(self, url, database, full_commit=True, session=None): 
        """Create a new Couch data container."""
        self._url = url
        self._full_commit = full_commit
        self._session = session
        self._server = Server(url=self._url,
                              full_commit=self._full_commit,
                              session=self._session)
        # this will ensure that transaction and sync logs exist and are
        # up-to-date.
        self.set_document_factory(LeapDocument)
        try:
            self._database = self._server[database]
        except ResourceNotFound:
            self._server.create(database)
            self._database = self._server[database]
        super(CouchDatabase, self).__init__()

    #-------------------------------------------------------------------------
    # implemented methods from Database
    #-------------------------------------------------------------------------

    def _get_doc(self, doc_id, check_for_conflicts=False):
        """Get just the document content, without fancy handling.
        
        Conflicts do not happen on server side, so there's no need to check
        for them.
        """
        cdoc = self._database.get(doc_id)
        if cdoc is None:
            return None
        content = {}
        for (key, value) in cdoc.items():
            if key not in ['_id', '_rev', 'u1db_rev']:
                content[key] = value
        doc = self._factory(doc_id=doc_id, rev=cdoc['u1db_rev'])
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

    def _put_doc(self, doc):
        # map u1db metadata to couch
        content = doc.content
        cdoc = Document()
        cdoc['_id'] = doc.doc_id
        cdoc['u1db_rev'] = doc.rev
        for (key, value) in content.items():
            cdoc[key] = value
        self._database.save(cdoc)

    def get_sync_target(self):
        return CouchSyncTarget(self)

    def close(self):
        raise NotImplementedError(self.close)

    def sync(self, url, creds=None, autocreate=True):
        from u1db.sync import Synchronizer
        from u1db.remote.http_target import CouchSyncTarget
        return Synchronizer(self, CouchSyncTarget(url, creds=creds)).sync(
            autocreate=autocreate)

    def _get_u1db_data(self):
        cdoc = self._database.get(self.U1DB_DATA_DOC_ID)
        self._sync_log.log = cdoc['sync_log']
        self._transaction_log.log = cdoc['transaction_log']
        self._replica_uid = cdoc['replica_uid']
        self._couch_rev = cdoc['_rev']

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


