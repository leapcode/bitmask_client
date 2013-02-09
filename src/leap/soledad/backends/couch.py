# general imports
import uuid
from base64 import b64encode, b64decode
import re
# u1db
from u1db import errors
from u1db.sync import LocalSyncTarget
from u1db.backends.inmemory import InMemoryIndex
from u1db.remote.server_state import ServerState
from u1db.errors import DatabaseDoesNotExist
# couchdb
from couchdb.client import Server, Document as CouchDocument
from couchdb.http import ResourceNotFound
# leap
from leap.soledad.backends.objectstore import ObjectStore
from leap.soledad.backends.leap_backend import LeapDocument

try:
    import simplejson as json
except ImportError:
    import json  # noqa


class InvalidURLError(Exception):
    pass


class CouchDatabase(ObjectStore):
    """A U1DB implementation that uses Couch as its persistence layer."""

    @classmethod
    def open_database(cls, url, create):
        # get database from url
        m = re.match('(^https?://[^/]+)/(.+)$', url)
        if not m:
            raise InvalidURLError
        url = m.group(1)
        dbname = m.group(2)
        server = Server(url=url)
        try:
            server[dbname]
        except ResourceNotFound:
            if not create:
                raise DatabaseDoesNotExist()
        return cls(url, dbname)

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
        try:
            self._database = self._server[database]
        except ResourceNotFound:
            self._server.create(database)
            self._database = self._server[database]
        super(CouchDatabase, self).__init__(replica_uid=replica_uid,
                                            document_factory=LeapDocument)

    #-------------------------------------------------------------------------
    # methods from Database
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

    def create_index(self, index_name, *index_expressions):
        if index_name in self._indexes:
            if self._indexes[index_name]._definition == list(
                    index_expressions):
                return
            raise errors.IndexNameTakenError
        index = InMemoryIndex(index_name, list(index_expressions))
        for doc_id in self._database:
            if doc_id == self.U1DB_DATA_DOC_ID:
                continue
            doc = self._get_doc(doc_id)
            if doc.content is not None:
                index.add_json(doc_id, doc.get_json())
        self._indexes[index_name] = index
        # save data in object store
        self._set_u1db_data()

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

    #-------------------------------------------------------------------------
    # methods from ObjectStore
    #-------------------------------------------------------------------------

    def _init_u1db_data(self):
        if self._replica_uid is None:
            self._replica_uid = uuid.uuid4().hex
        doc = self._factory(doc_id=self.U1DB_DATA_DOC_ID)
        doc.content = {'transaction_log': [],
                       'conflicts': b64encode(json.dumps({})),
                       'other_generations': {},
                       'indexes': b64encode(json.dumps({})),
                       'replica_uid': self._replica_uid}
        self._put_doc(doc)

    def _get_u1db_data(self):
        # retrieve u1db data from couch db
        cdoc = self._database.get(self.U1DB_DATA_DOC_ID)
        jsonstr = self._database.get_attachment(cdoc, 'u1db_json').getvalue()
        content = json.loads(jsonstr)
        # set u1db database info
        #self._sync_log = content['sync_log']
        self._transaction_log = content['transaction_log']
        self._conflicts = json.loads(b64decode(content['conflicts']))
        self._other_generations = content['other_generations']
        self._indexes = self._load_indexes_from_json(
            b64decode(content['indexes']))
        self._replica_uid = content['replica_uid']
        # save couch _rev
        self._couch_rev = cdoc['_rev']

    def _set_u1db_data(self):
        doc = self._factory(doc_id=self.U1DB_DATA_DOC_ID)
        doc.content = {
            'transaction_log': self._transaction_log,
            # Here, the b64 encode ensures that document content
            # does not cause strange behaviour in couchdb because
            # of encoding.
            'conflicts': b64encode(json.dumps(self._conflicts)),
            'other_generations': self._other_generations,
            'indexes': b64encode(self._dump_indexes_as_json()),
            'replica_uid': self._replica_uid,
            '_rev': self._couch_rev}
        self._put_doc(doc)

    #-------------------------------------------------------------------------
    # Couch specific methods
    #-------------------------------------------------------------------------

    def delete_database(self):
        del(self._server[self._dbname])

    def _dump_indexes_as_json(self):
        indexes = {}
        for name, idx in self._indexes.iteritems():
            indexes[name] = {}
            for attr in ['name', 'definition', 'values']:
                indexes[name][attr] = getattr(idx, '_' + attr)
        return json.dumps(indexes)

    def _load_indexes_from_json(self, indexes):
        dict = {}
        for name, idx_dict in json.loads(indexes).iteritems():
            idx = InMemoryIndex(name, idx_dict['definition'])
            idx._values = idx_dict['values']
            dict[name] = idx
        return dict


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


class CouchServerState(ServerState):
    """
    Inteface of the WSGI server with the CouchDB backend.
    """

    def __init__(self, couch_url):
        self.couch_url = couch_url

    def open_database(self, dbname):
        # TODO: open couch
        from leap.soledad.backends.couch import CouchDatabase
        return CouchDatabase.open_database(self.couch_url + '/' + dbname,
                                           create=False)

    def ensure_database(self, dbname):
        from leap.soledad.backends.couch import CouchDatabase
        db = CouchDatabase.open_database(self.couch_url + '/' + dbname,
                                         create=True)
        return db, db._replica_uid

    def delete_database(self, dbname):
        from leap.soledad.backends.couch import CouchDatabase
        CouchDatabase.delete_database(self.couch_url + '/' + dbname)
