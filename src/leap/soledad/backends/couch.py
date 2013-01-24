import uuid
from base64 import b64encode, b64decode
from u1db.sync import LocalSyncTarget
from couchdb.client import Server, Document as CouchDocument
from couchdb.http import ResourceNotFound
from leap.soledad.backends.objectstore import ObjectStore
from leap.soledad.backends.leap_backend import LeapDocument

try:
    import simplejson as json
except ImportError:
    import json  # noqa


class CouchDatabase(ObjectStore):
    """A U1DB implementation that uses Couch as its persistence layer."""

    def __init__(self, url, database, replica_uid=None, full_commit=True,
                 session=None):
        """Create a new Couch data container."""
        self._url = url
        self._full_commit = full_commit
        self._session = session
        self._server = Server(url=self._url,
                              full_commit=self._full_commit,
                              session=self._session)
        self._dbname = database
        # this will ensure that transaction and sync logs exist and are
        # up-to-date.
        self.set_document_factory(LeapDocument)
        try:
            self._database = self._server[database]
        except ResourceNotFound:
            self._server.create(database)
            self._database = self._server[database]
        super(CouchDatabase, self).__init__(replica_uid=replica_uid)

    #-------------------------------------------------------------------------
    # implemented methods from Database
    #-------------------------------------------------------------------------

    def _get_doc(self, doc_id, check_for_conflicts=False):
        """
        Get just the document content, without fancy handling.
        """
        cdoc = self._database.get(doc_id)
        if cdoc is None:
            return None
        has_conflicts = False
        if check_for_conflicts:
            has_conflicts = self._has_conflicts(doc_id)
        doc = self._factory(
            doc_id=doc_id,
            rev=cdoc['u1db_rev'],
            has_conflicts=has_conflicts)
        contents = self._database.get_attachment(cdoc, 'u1db_json')
        if contents:
            doc.content = json.loads(contents.getvalue())
        else:
            doc.make_tombstone()
        return doc

    def get_all_docs(self, include_deleted=False):
        """Get all documents from the database."""
        generation = self._get_generation()
        results = []
        for doc_id in self._database:
            if doc_id == self.U1DB_DATA_DOC_ID:
                continue
            doc = self._get_doc(doc_id, check_for_conflicts=True)
            if doc.content is None and not include_deleted:
                continue
            results.append(doc)
        return (generation, results)

    def _put_doc(self, doc):
        # prepare couch's Document
        cdoc = CouchDocument()
        cdoc['_id'] = doc.doc_id
        # we have to guarantee that couch's _rev is cosistent
        old_cdoc = self._database.get(doc.doc_id)
        if old_cdoc is not None:
            cdoc['_rev'] = old_cdoc['_rev']
        # store u1db's rev
        cdoc['u1db_rev'] = doc.rev
        # save doc in db
        self._database.save(cdoc)
        # store u1db's content as json string
        if not doc.is_tombstone():
            self._database.put_attachment(cdoc, doc.get_json(),
                                          filename='u1db_json')
        else:
            self._database.delete_attachment(cdoc, 'u1db_json')

    def get_sync_target(self):
        return CouchSyncTarget(self)

    def close(self):
        # TODO: fix this method so the connection is properly closed and
        # test_close (+tearDown, which deletes the db) works without problems.
        self._url = None
        self._full_commit = None
        self._session = None
        #self._server = None
        self._database = None
        return True

    def sync(self, url, creds=None, autocreate=True):
        from u1db.sync import Synchronizer
        return Synchronizer(self, CouchSyncTarget(url, creds=creds)).sync(
            autocreate=autocreate)

    def _initialize(self):
        if self._replica_uid is None:
            self._replica_uid = uuid.uuid4().hex
        doc = self._factory(doc_id=self.U1DB_DATA_DOC_ID)
        doc.content = {'sync_log': [],
                       'transaction_log': [],
                       'conflict_log': b64encode(json.dumps([])),
                       'replica_uid': self._replica_uid}
        self._put_doc(doc)

    def _get_u1db_data(self):
        cdoc = self._database.get(self.U1DB_DATA_DOC_ID)
        jsonstr = self._database.get_attachment(cdoc, 'u1db_json').getvalue()
        content = json.loads(jsonstr)
        self._sync_log.log = content['sync_log']
        self._transaction_log.log = content['transaction_log']
        self._conflict_log.log = json.loads(b64decode(content['conflict_log']))
        self._replica_uid = content['replica_uid']
        self._couch_rev = cdoc['_rev']

    def _set_u1db_data(self):
        doc = self._factory(doc_id=self.U1DB_DATA_DOC_ID)
        doc.content = {
            'sync_log': self._sync_log.log,
            'transaction_log': self._transaction_log.log,
            # Here, the b64 encode ensures that document content
            # does not cause strange behaviour in couchdb because
            # of encoding.
            'conflict_log': b64encode(json.dumps(self._conflict_log.log)),
            'replica_uid': self._replica_uid,
            '_rev': self._couch_rev}
        self._put_doc(doc)

    #-------------------------------------------------------------------------
    # Couch specific methods
    #-------------------------------------------------------------------------

    def delete_database(self):
        del(self._server[self._dbname])


class CouchSyncTarget(LocalSyncTarget):

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
