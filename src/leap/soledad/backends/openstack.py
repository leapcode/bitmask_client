# TODO: this backend is not tested yet.
from u1db.remote.http_target import HTTPSyncTarget
import swiftclient
from soledad.backends.objectstore import ObjectStore


class OpenStackDatabase(ObjectStore):
    """A U1DB implementation that uses OpenStack as its persistence layer."""

    def __init__(self, auth_url, user, auth_key, container):
        """Create a new OpenStack data container."""
        self._auth_url = auth_url
        self._user = user
        self._auth_key = auth_key
        self._container = container
        self._connection = swiftclient.Connection(self._auth_url, self._user,
                                                  self._auth_key)
        self._get_auth()
        # this will ensure transaction and sync logs exist and are up-to-date.
        super(OpenStackDatabase, self).__init__()

    #-------------------------------------------------------------------------
    # implemented methods from Database
    #-------------------------------------------------------------------------

    def _get_doc(self, doc_id, check_for_conflicts=False):
        """Get just the document content, without fancy handling.

        Conflicts do not happen on server side, so there's no need to check
        for them.
        """
        try:
            response, contents = self._connection.get_object(self._container,
                                                             doc_id)
            # TODO: change revision to be a dictionary element?
            rev = response['x-object-meta-rev']
            return self._factory(doc_id, rev, contents)
        except swiftclient.ClientException:
            return None

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

    def _put_doc(self, doc, new_rev):
        new_rev = self._allocate_doc_rev(doc.rev)
        # TODO: change revision to be a dictionary element?
        headers = {'X-Object-Meta-Rev': new_rev}
        self._connection.put_object(self._container, doc_id, doc.get_json(),
                                    headers=headers)

    def get_sync_target(self):
        return OpenStackSyncTarget(self)

    def close(self):
        raise NotImplementedError(self.close)

    def sync(self, url, creds=None, autocreate=True):
        from u1db.sync import Synchronizer
        from u1db.remote.http_target import OpenStackSyncTarget
        return Synchronizer(self, OpenStackSyncTarget(url, creds=creds)).sync(
            autocreate=autocreate)

    #-------------------------------------------------------------------------
    # OpenStack specific methods
    #-------------------------------------------------------------------------

    def _get_auth(self):
        self._url, self._auth_token = self._connection.get_auth()
        return self._url, self.auth_token


class OpenStackSyncTarget(HTTPSyncTarget):

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
