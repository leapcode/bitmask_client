from leap import *
from u1db import errors
from u1db.backends import CommonBackend
from u1db.remote.http_target import HTTPSyncTarget
from swiftclient import client


class OpenStackDatabase(CommonBackend):
    """A U1DB implementation that uses OpenStack as its persistence layer."""

    def __init__(self, auth_url, user, auth_key, container):
        """Create a new OpenStack data container."""
        self._auth_url = auth_url
        self._user = user
        self._auth_key = auth_key
        self._container = container
        self.set_document_factory(LeapDocument)
        self._connection = swiftclient.Connection(self._auth_url, self._user,
                                                  self._auth_key)
        self._get_auth()

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
        # TODO: support deleted docs?
        headers = self._connection.head_object(self._container, doc_id)
        rev = headers['x-object-meta-rev']
        response, contents = self._connection.get_object(self._container, doc_id)
        return self._factory(doc_id, rev, contents)

    def get_all_docs(self, include_deleted=False):
        """Get all documents from the database."""
        raise NotImplementedError(self.get_all_docs)

    def put_doc(self, doc):
        if doc.doc_id is None:
            raise errors.InvalidDocId()
        self._check_doc_id(doc.doc_id)
        self._check_doc_size(doc)
        # TODO: check for conflicts?
        new_rev = self._allocate_doc_rev(doc.rev)
        headers = { 'X-Object-Meta-Rev' : new_rev }
        self._connection.put_object(self._container, doc_id, doc.get_json(),
                                    headers=headers)
        return new_rev

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
        self._update_u1db_data()
        return self._sync_log.get_replica_gen_and_trans_id(other_replica_uid)

    def _set_replica_gen_and_trans_id(self, other_replica_uid,
                                      other_generation, other_transaction_id):
        self._update_u1db_data()
        return self._sync_log.set_replica_gen_and_trans_id(other_replica_uid,
                                other_generation, other_transaction_id)

    #-------------------------------------------------------------------------
    # implemented methods from CommonBackend
    #-------------------------------------------------------------------------

    def _get_generation(self):
        self._update_u1db_data()
        return self._transaction_log.get_generation()

    def _get_generation_info(self):
        self._update_u1db_data()
        return self._transaction_log.get_generation_info()

    def _get_doc(self, doc_id, check_for_conflicts=False):
        """Get just the document content, without fancy handling."""
        raise NotImplementedError(self._get_doc)

    def _has_conflicts(self, doc_id):
        raise NotImplementedError(self._has_conflicts)

    def _put_and_update_indexes(self, doc_id, old_doc, new_rev, content):
        raise NotImplementedError(self._put_and_update_indexes)


    def _get_trans_id_for_gen(self, generation):
        self._update_u1db_data()
        trans_id = self._transaction_log.get_trans_id_for_gen(generation)
        if trans_id is None:
            raise errors.InvalidGeneration
        return trans_id

    #-------------------------------------------------------------------------
    # OpenStack specific methods
    #-------------------------------------------------------------------------

    def _is_initialized(self, c):
        raise NotImplementedError(self._is_initialized)

    def _initialize(self, c):
        raise NotImplementedError(self._initialize)

    def _get_auth(self):
        self._url, self._auth_token = self._connection.get_auth()
        return self._url, self.auth_token

    def _update_u1db_data(self):
        data = self.get_doc('u1db_data').content
        self._transaction_log = data['transaction_log']
        self._sync_log = data['sync_log']


class OpenStackSyncTarget(HTTPSyncTarget):

    def get_sync_info(self, source_replica_uid):
        raise NotImplementedError(self.get_sync_info)

    def record_sync_info(self, source_replica_uid, source_replica_generation,
                         source_replica_transaction_id):
        raise NotImplementedError(self.record_sync_info)


class SimpleLog(object):
    def __init__(self, log=None):
        self._log = []
        if log:
            self._log = log

    def append(self, msg):
        self._log.append(msg)

    def reduce(self, func, initializer=None):
        return reduce(func, self._log, initializer)

    def map(self, func):
        return map(func, self._log)


class TransactionLog(SimpleLog):
    """
    A list of (generation, doc_id, transaction_id) tuples.
    """

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
        if not self._log:
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

class SyncLog(SimpleLog):
    """
    A list of (replica_id, generation, transaction_id) tuples.
    """

    def find_by_replica_uid(self, replica_uid):
        if not self._log:
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
        old_log = self._log
        self._log = []
        for log in old_log:
            if log[0] != other_replica_uid:
                self.append(log)
        self.append((other_replica_uid, other_generation,
                     other_transaction_id))
                
