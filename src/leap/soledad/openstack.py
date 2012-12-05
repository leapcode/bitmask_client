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
        # This method is implemented in TransactionLog because testing is
        # easier like this for now, but it can be moved to here afterwards.
        return self._transaction_log.whats_changed(old_generation)

    def _get_doc(self, doc_id, check_for_conflicts=False):
        """Get just the document content, without fancy handling.
        
        Conflicts do not happen on server side, so there's no need to check
        for them.
        """
        try:
            response, contents = self._connection.get_object(self._container, doc_id)
            rev = response['x-object-meta-rev']
            return self._factory(doc_id, rev, contents)
        except: swiftclient.ClientException
            return None

    def get_doc(self, doc_id, include_deleted=False):
        doc = self._get_doc(doc_id, check_for_conflicts=True)
        if doc is None:
            return None
        if doc.is_tombstone() and not include_deleted:
            return None
        return doc

    def get_all_docs(self, include_deleted=False):
        """Get all documents from the database."""
        generation = self._get_generation()
        results = []
        _, doc_ids = self._connection.get_container(self._container,
                                                    full_listing=True)
        for doc_id in doc_ids:
            doc = self._get_doc(doc_id)
            if doc.content is None and not include_deleted:
                continue
            results.append(doc)
        return (generation, results)

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
        new_gen = self._get_generation() + 1
        trans_id = self._allocate_transaction_id()
        self._transaction_log.append((new_gen, doc.doc_id, trans_id))
        self._set_u1db_data()
        return new_rev

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

    def get_sync_target(self):
        return OpenStackSyncTarget(self)

    def close(self):
        raise NotImplementedError(self.close)

    def sync(self, url, creds=None, autocreate=True):
        from u1db.sync import Synchronizer
        from u1db.remote.http_target import OpenStackSyncTarget
        return Synchronizer(self, OpenStackSyncTarget(url, creds=creds)).sync(
            autocreate=autocreate)

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

    #-------------------------------------------------------------------------
    # OpenStack specific methods
    #-------------------------------------------------------------------------

    def _ensure_u1db_data(self):
        """
        Guarantee that u1db data exists in store.
        """
        if self._is_initialized():
            return
        self._initialize()

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
        content = { 'transaction_log' = [],
                    'sync_log' = [] }
        doc = self.create_doc('u1db_data', content)

    def _get_auth(self):
        self._url, self._auth_token = self._connection.get_auth()
        return self._url, self.auth_token

    def _get_u1db_data(self):
        data = self.get_doc('u1db_data').content
        self._transaction_log = data['transaction_log']
        self._sync_log = data['sync_log']

    def _set_u1db_data(self):
        doc = self._factory('u1db_data')
        doc.content = { 'transaction_log' : self._transaction_log,
                        'sync_log'        : self._sync_log }
        self.put_doc(doc)


class OpenStackSyncTarget(HTTPSyncTarget):

    def get_sync_info(self, source_replica_uid):
        raise NotImplementedError(self.get_sync_info)

    def record_sync_info(self, source_replica_uid, source_replica_generation,
                         source_replica_transaction_id):
        raise NotImplementedError(self.record_sync_info)


class SimpleLog(object):
    def __init__(self):
        self._log = []

    def _set_log(self, log):
        self._log = log

    def _get_log(self):
        return self._log

    log = property(
        _get_log, _set_log, doc="Log contents.")

    def append(self, msg):
        self._log.append(msg)

    def reduce(self, func, initializer=None):
        return reduce(func, self.log, initializer)

    def map(self, func):
        return map(func, self.log)

    def filter(self, func):
        return filter(func, self.log)


class TransactionLog(SimpleLog):
    """
    A list of (generation, doc_id, transaction_id) tuples.
    """

    def _set_log(self, log):
        self._log = log

    def _get_log(self):
        return sorted(self._log, reverse=True)

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

    def whats_changed(self, old_generation):
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
            results = self.log
            if not results:
                cur_gen = 0
                newest_trans_id = ''
            else:
                cur_gen, _, newest_trans_id = results[0]

        return cur_gen, newest_trans_id, changes
        


class SyncLog(SimpleLog):
    """
    A list of (replica_id, generation, transaction_id) tuples.
    """

    def find_by_replica_uid(self, replica_uid):
        if not self.log:
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
        self.log = self.filter(lambda x: x[0] != other_replica_uid)
        self.append((other_replica_uid, other_generation,
                     other_transaction_id))

