from u1db.backends import CommonBackend
from u1db import errors, Document, vectorclock

class ObjectStore(CommonBackend):
    """
    A backend for storing u1db data in an object store.
    """

    def __init__(self, replica_uid=None):
        # This initialization method should be called after the connection
        # with the database is established in each implementation, so it can
        # ensure that u1db data is configured and up-to-date.
        self.set_document_factory(Document)
        self._sync_log = SyncLog()
        self._transaction_log = TransactionLog()
        self._conflict_log = ConflictLog(self._factory)
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
        self._put_and_update_indexes(old_doc, doc)
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
        self._put_and_update_indexes(old_doc, doc)
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
        self._get_u1db_data()
        conflict_docs = self._conflict_log.get_conflicts(doc_id)
        if not conflict_docs:
            return []
        this_doc = self._get_doc(doc_id)
        this_doc.has_conflicts = True
        return [this_doc] + list(conflict_docs)

    def resolve_doc(self, doc, conflicted_doc_revs):
        cur_doc = self._get_doc(doc.doc_id)
        new_rev = self._ensure_maximal_rev(cur_doc.rev,
                                           conflicted_doc_revs)
        superseded_revs = set(conflicted_doc_revs)
        doc.rev = new_rev
        if cur_doc.rev in superseded_revs:
            self._put_and_update_indexes(cur_doc, doc)
        else:
            self._add_conflict(doc.doc_id, new_rev, doc.get_json())
        self._delete_conflicts(doc, superseded_revs)

    def _get_replica_gen_and_trans_id(self, other_replica_uid):
        self._get_u1db_data()
        return self._sync_log.get_replica_gen_and_trans_id(other_replica_uid)

    def _set_replica_gen_and_trans_id(self, other_replica_uid,
                                      other_generation, other_transaction_id):
        return self._do_set_replica_gen_and_trans_id(
                 other_replica_uid,
                 other_generation,
                 other_transaction_id)

    def _do_set_replica_gen_and_trans_id(self, other_replica_uid,
                                         other_generation, other_transaction_id):
        self._sync_log.set_replica_gen_and_trans_id(other_replica_uid,
                                                    other_generation,
                                                    other_transaction_id)
        self._set_u1db_data()

    def _get_transaction_log(self):
        self._get_u1db_data()
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
        self._get_u1db_data()
        return self._conflict_log.has_conflicts(doc_id)

    def _put_and_update_indexes(self, old_doc, doc):
        # for now we ignore indexes as this backend is used to store encrypted
        # blobs of data in the server.
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
        NotImplementedError(self._initialize)

    def _get_u1db_data(self):
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
        self._set_u1db_data()

    def _delete_conflicts(self, doc, conflict_revs):
        deleting = [(doc.doc_id, c_rev) for c_rev in conflict_revs]
        self._conflict_log.delete_conflicts(deleting)
        self._set_u1db_data()
        doc.has_conflicts = self._has_conflicts(doc.doc_id)

    def _prune_conflicts(self, doc, doc_vcr):
        if self._has_conflicts(doc.doc_id):
            autoresolved = False
            c_revs_to_prune = []
            for c_doc in self._conflict_log.get_conflicts(doc.doc_id):
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
            self._delete_conflicts(doc, c_revs_to_prune)

    def _force_doc_sync_conflict(self, doc):
        my_doc = self._get_doc(doc.doc_id)
        self._prune_conflicts(doc, vectorclock.VectorClockRev(doc.rev))
        self._add_conflict(doc.doc_id, my_doc.rev, my_doc.get_json())
        doc.has_conflicts = True
        self._put_and_update_indexes(my_doc, doc)


#----------------------------------------------------------------------------
# U1DB's TransactionLog, SyncLog, ConflictLog, and Index
#----------------------------------------------------------------------------

class SimpleList(object):
    def __init__(self):
        self._data = []

    def _set_data(self, data):
        self._data = data

    def _get_data(self):
        return self._data

    data = property(
        _get_data, _set_data, doc="List contents.")

    def append(self, msg):
        self._data.append(msg)

    def reduce(self, func, initializer=None):
        return reduce(func, self._data, initializer)

    def map(self, func):
        return map(func, self._get_data())

    def filter(self, func):
        return filter(func, self._get_data())


class SimpleLog(SimpleList):

    def _set_log(self, log):
        self._data = log

    def _get_log(self):
        return self._data

    log = property(
        _get_log, _set_log, doc="Log contents.")


class TransactionLog(SimpleLog):
    """
    An ordered list of (generation, doc_id, transaction_id) tuples.
    """

    def _set_log(self, log):
        self._data = log

    def _get_data(self, reverse=True):
        return sorted(self._data, reverse=reverse)

    _get_log = _get_data

    log = property(
        _get_log, _set_log, doc="Log contents.")

    def get_generation(self):
        """
        Return the current generation.
        """
        gens = self.map(lambda x: x[0])
        if not gens:
            return 0
        return max(gens)

    def get_generation_info(self):
        """
        Return the current generation and transaction id.
        """
        if not self._get_log():
            return(0, '')
        info = self.map(lambda x: (x[0], x[2]))
        return reduce(lambda x, y: x if (x[0] > y[0]) else y, info)

    def get_trans_id_for_gen(self, gen):
        """
        Get the transaction id corresponding to a particular generation.
        """
        log = self.reduce(lambda x, y: y if y[0] == gen else x)
        if log is None:
            return None
        return log[2]

    def whats_changed(self, old_generation):
        """
        Return a list of documents that have changed since old_generation.
        """
        results = self.filter(lambda x: x[0] > old_generation)
        seen = set()
        changes = []
        newest_trans_id = ''
        for generation, doc_id, trans_id in results:
            if doc_id not in seen:
                changes.append((doc_id, generation, trans_id))
                seen.add(doc_id)
        if changes:
            cur_gen = changes[0][1]  # max generation
            newest_trans_id = changes[0][2]
            changes.reverse()
        else:
            results = self._get_log()
            if not results:
                cur_gen = 0
                newest_trans_id = ''
            else:
                cur_gen, _, newest_trans_id = results[0]

        return cur_gen, newest_trans_id, changes


    def get_transaction_log(self):
        """
        Return only a list of (doc_id, transaction_id)
        """
        return map(lambda x: (x[1], x[2]), sorted(self._get_log(reverse=False)))


class SyncLog(SimpleLog):
    """
    A list of (replica_id, generation, transaction_id) tuples.
    """

    def find_by_replica_uid(self, replica_uid):
        if not self._get_log():
            return ()
        return self.reduce(lambda x, y: y if y[0] == replica_uid else x)

    def get_replica_gen_and_trans_id(self, other_replica_uid):
        """
        Return the last known generation and transaction id for the other db
        replica.
        """
        info = self.find_by_replica_uid(other_replica_uid)
        if not info:
            return (0, '')
        return (info[1], info[2])

    def set_replica_gen_and_trans_id(self, other_replica_uid,
                                      other_generation, other_transaction_id):
        """
        Set the last-known generation and transaction id for the other
        database replica.
        """
        self._set_log(self.filter(lambda x: x[0] != other_replica_uid))
        self.append((other_replica_uid, other_generation,
                     other_transaction_id))

class ConflictLog(SimpleLog):
    """
    A list of (doc_id, my_doc_rev, my_content) tuples.
    """

    def __init__(self, factory):
        super(ConflictLog, self).__init__()
        self._factory = factory
    
    def delete_conflicts(self, conflicts):
        for conflict in conflicts:
            self._set_log(self.filter(lambda x:
                          x[0] != conflict[0] or x[1] != conflict[1]))

    def get_conflicts(self, doc_id):
        conflicts = self.filter(lambda x: x[0] == doc_id)
        if not conflicts:
            return []
        return reversed(map(lambda x: self._factory(doc_id, x[1], x[2]),
                            conflicts))

    def has_conflicts(self, doc_id):
        return bool(self.filter(lambda x: x[0] == doc_id))

