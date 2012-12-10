from u1db.backends import CommonBackend


class ObjectStore(CommonBackend):

    def __init__(self):
        self._sync_log = SyncLog()
        self._transaction_log = TransactionLog()

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
        self._put_doc(olddoc)
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

    def _put_and_update_indexes(self, doc_id, old_doc, new_rev, content):
        raise NotImplementedError(self._put_and_update_indexes)


    def _get_trans_id_for_gen(self, generation):
        self._get_u1db_data()
        trans_id = self._transaction_log.get_trans_id_for_gen(generation)
        if trans_id is None:
            raise errors.InvalidGeneration
        return trans_id

    def _ensure_u1db_data(self):
        """
        Guarantee that u1db data exists in store.
        """
        if not self._is_initialized():
            self._initialize()
        u1db_data = self._get_doc('u1db_data')
        self._sync_log.log = u1db_data.content['sync_log']
        self._transaction_log.log = u1db_data.content['transaction_log']

    def _is_initialized(self):
        """
        Verify if u1db data exists in store.
        """
        if not self._get_doc('u1db_data'):
            return False
        return True

    def _initialize(self):
        """
        Create u1db data object in store.
        """
        content = { 'transaction_log' : [],
                    'sync_log' : [] }
        doc = self.create_doc('u1db_data', content)

    def _get_u1db_data(self):
        data = self.get_doc('u1db_data').content
        self._transaction_log = data['transaction_log']
        self._sync_log = data['sync_log']

    def _set_u1db_data(self):
        doc = self._factory('u1db_data')
        doc.content = { 'transaction_log' : self._transaction_log,
                        'sync_log'        : self._sync_log }
        self.put_doc(doc)


