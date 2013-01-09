import uuid
from u1db.backends import CommonBackend
from u1db import errors, Document
from leap.soledad import util as soledadutil


class ObjectStore(CommonBackend):
    """
    A backend for storing u1db data in an object store.
    """

    def __init__(self, replica_uid=None):
        # This initialization method should be called after the connection
        # with the database is established, so it can ensure that u1db data is
        # configured and up-to-date.
        self.set_document_factory(Document)
        self._sync_log = soledadutil.SyncLog()
        self._transaction_log = soledadutil.TransactionLog()
        self._conflict_log = soledadutil.ConflictLog()
        self._replica_uid = replica_uid
        self._ensure_u1db_data()

    #-------------------------------------------------------------------------
    # implemented methods from Database
    #-------------------------------------------------------------------------

    def set_document_factory(self, factory):
        self._factory = factory

    def set_document_size_limit(self, limit):
        raise NotImplementedError(self.set_document_size_limit)

    def whats_changed(self, old_generation=0):
        self._get_u1db_data()
        return self._transaction_log.whats_changed(old_generation)

    def get_doc(self, doc_id, include_deleted=False):
        doc = self._get_doc(doc_id, check_for_conflicts=True)
        if doc is None:
            return None
        if doc.is_tombstone() and not include_deleted:
            return None
        return doc

    def _put_doc(self, doc):
        raise NotImplementedError(self._put_doc)

    def _update_gen_and_transaction_log(self, doc_id):
        new_gen = self._get_generation() + 1
        trans_id = self._allocate_transaction_id()
        self._transaction_log.append((new_gen, doc_id, trans_id))
        self._set_u1db_data()

    def put_doc(self, doc):
        # consistency check
        if doc.doc_id is None:
            raise errors.InvalidDocId()
        self._check_doc_id(doc.doc_id)
        self._check_doc_size(doc)
        # check if document exists
        old_doc = self._get_doc(doc.doc_id, check_for_conflicts=True)
        if old_doc and old_doc.has_conflicts:
            raise errors.ConflictedDoc()
        if old_doc and doc.rev is None and old_doc.is_tombstone():
            new_rev = self._allocate_doc_rev(old_doc.rev)
        else:
            if old_doc is not None:
                if old_doc.rev != doc.rev:
                    raise errors.RevisionConflict()
            else:
                if doc.rev is not None:
                    raise errors.RevisionConflict()
            new_rev = self._allocate_doc_rev(doc.rev)
        doc.rev = new_rev
        self._put_doc(doc)
        self._update_gen_and_transaction_log(doc.doc_id)
        return doc.rev

    def delete_doc(self, doc):
        old_doc = self._get_doc(doc.doc_id, check_for_conflicts=True)
        if old_doc is None:
            raise errors.DocumentDoesNotExist
        if old_doc.rev != doc.rev:
            raise errors.RevisionConflict()
        if old_doc.is_tombstone():
            raise errors.DocumentAlreadyDeleted
        if old_doc.has_conflicts:
            raise errors.ConflictedDoc()
        new_rev = self._allocate_doc_rev(doc.rev)
        doc.rev = new_rev
        doc.make_tombstone()
        self._put_doc(doc)
        self._update_gen_and_transaction_log(doc.doc_id)
        return new_rev

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

    def _get_replica_gen_and_trans_id(self, other_replica_uid):
        self._get_u1db_data()
        return self._sync_log.get_replica_gen_and_trans_id(other_replica_uid)

    def _set_replica_gen_and_trans_id(self, other_replica_uid,
                                      other_generation, other_transaction_id):
        self._get_u1db_data()
        self._sync_log.set_replica_gen_and_trans_id(other_replica_uid,
                                                    other_generation,
                                                    other_transaction_id)
        self._set_u1db_data()

    def _do_set_replica_gen_and_trans_id(self, other_replica_uid,
                                         other_generation, other_transaction_id):
        return self._set_replica_gen_and_trans_id(
                 other_replica_uid,
                 other_generation,
                 other_transaction_id)

    def _get_transaction_log(self):
        return self._transaction_log.get_transaction_log()

    #-------------------------------------------------------------------------
    # implemented methods from CommonBackend
    #-------------------------------------------------------------------------

    def _get_generation(self):
        self._get_u1db_data()
        return self._transaction_log.get_generation()

    def _get_generation_info(self):
        self._get_u1db_data()
        return self._transaction_log.get_generation_info()

    def _has_conflicts(self, doc_id):
        # Documents never have conflicts on server.
        return False

    def _put_and_update_indexes(self, old_doc, doc):
        # TODO: implement index update
        self._put_doc(doc)
        self._update_gen_and_transaction_log(doc.doc_id)

    def _get_trans_id_for_gen(self, generation):
        self._get_u1db_data()
        trans_id = self._transaction_log.get_trans_id_for_gen(generation)
        if trans_id is None:
            raise errors.InvalidGeneration
        return trans_id

    #-------------------------------------------------------------------------
    # methods specific for object stores
    #-------------------------------------------------------------------------

    def _ensure_u1db_data(self):
        """
        Guarantee that u1db data (logs and replica info) exists in store.
        """
        if not self._is_initialized():
            self._initialize()
        self._get_u1db_data()

    U1DB_DATA_DOC_ID = 'u1db_data'

    def _is_initialized(self):
        """
        Verify if u1db data exists in store.
        """
        doc = self._get_doc(self.U1DB_DATA_DOC_ID)
        if not self._get_doc(self.U1DB_DATA_DOC_ID):
            return False
        return True

    def _initialize(self):
        """
        Create u1db data object in store.
        """
        if self._replica_uid is None:
            self._replica_uid = uuid.uuid4().hex
        doc = self._factory(doc_id=self.U1DB_DATA_DOC_ID)
        doc.content = { 'sync_log' : [],
                        'transaction_log' : [],
                        'conflict_log' : [],
                        'replica_uid' : self._replica_uid }
        self._put_doc(doc)

    def _get_u1db_data(self, u1db_data_doc_id):
        """
        Fetch u1db configuration data from backend storage.
        """
        NotImplementedError(self._get_u1db_data)

    def _set_u1db_data(self):
        """
        Save u1db configuration data on backend storage.
        """
        NotImplementedError(self._set_u1db_data)

    def _set_replica_uid(self, replica_uid):
        self._replica_uid = replica_uid
        self._set_u1db_data()

    def _get_replica_uid(self):
        return self._replica_uid

    replica_uid = property(
        _get_replica_uid, _set_replica_uid, doc="Replica UID of the database")


    #-------------------------------------------------------------------------
    # The methods below were cloned from u1db sqlite backend. They should at
    # least exist and raise a NotImplementedError exception in CommonBackend
    # (should we maybe fill a bug in u1db bts?).
    #-------------------------------------------------------------------------

    def _add_conflict(self, doc_id, my_doc_rev, my_content):
        self._conflict_log.append((doc_id, my_doc_rev, my_content))

    def _delete_conflicts(self, doc, conflict_revs):
        deleting = [(doc.doc_id, c_rev) for c_rev in conflict_revs]
        self._conflict_log.delete_conflicts(deleting)
        doc.has_conflicts = self._has_conflicts(doc.doc_id)

    def _prune_conflicts(self, doc, doc_vcr):
        if self._has_conflicts(doc.doc_id):
            autoresolved = False
            c_revs_to_prune = []
            for c_doc in self._get_conflicts(doc.doc_id):
                c_vcr = vectorclock.VectorClockRev(c_doc.rev)
                if doc_vcr.is_newer(c_vcr):
                    c_revs_to_prune.append(c_doc.rev)
                elif doc.same_content_as(c_doc):
                    c_revs_to_prune.append(c_doc.rev)
                    doc_vcr.maximize(c_vcr)
                    autoresolved = True
            if autoresolved:
                doc_vcr.increment(self._replica_uid)
                doc.rev = doc_vcr.as_str()
            c = self._db_handle.cursor()
            self._delete_conflicts(c, doc, c_revs_to_prune)
