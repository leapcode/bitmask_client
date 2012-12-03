# License?

"""A U1DB implementation that uses OpenStack Swift as its persistence layer."""

try:
    import simplejson as json
except ImportError:
    import json  # noqa

from u1db.backends import CommonBackend, CommonSyncTarget
from u1db import (
    Document,
    errors,
    query_parser,
    vectorclock,
    )

from swiftclient import client
import base64


class OpenStackDatabase(CommonBackend):
    """A U1DB implementation that uses OpenStack as its persistence layer."""

    def __init__(self, auth_url, user, auth_key):
        """Create a new OpenStack data container."""
        self._auth_url = auth_url
        self._user = user
        self._auth_key = auth_key
        self.set_document_factory(LeapDocument)
        self._connection = swiftclient.Connection(self._auth_url, self._user,
                                                  self._auth_key)

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
        raise NotImplementedError(self.get_doc)

    def get_all_docs(self, include_deleted=False):
        """Get all documents from the database."""
        raise NotImplementedError(self.get_all_docs)

    def put_doc(self, doc):
        raise NotImplementedError(self.put_doc)

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
        raise NotImplementedError(self._get_replica_gen_and_trans_id)

    def _set_replica_gen_and_trans_id(self, other_replica_uid,
                                      other_generation, other_transaction_id):
        raise NotImplementedError(self._set_replica_gen_and_trans_id)

    #-------------------------------------------------------------------------
    # implemented methods from CommonBackend
    #-------------------------------------------------------------------------

    def _get_generation(self):
        raise NotImplementedError(self._get_generation)

    def _get_generation_info(self):
        raise NotImplementedError(self._get_generation_info)

    def _get_doc(self, doc_id, check_for_conflicts=False):
        """Get just the document content, without fancy handling."""
        raise NotImplementedError(self._get_doc)

    def _has_conflicts(self, doc_id):
        raise NotImplementedError(self._has_conflicts)

    def _get_transaction_log(self):
        raise NotImplementedError(self._get_transaction_log)

    def _put_and_update_indexes(self, doc_id, old_doc, new_rev, content):
        raise NotImplementedError(self._put_and_update_indexes)


    def _get_trans_id_for_gen(self, generation):
        raise NotImplementedError(self._get_trans_id_for_gen)

    #-------------------------------------------------------------------------
    # OpenStack specific methods
    #-------------------------------------------------------------------------

    def _is_initialized(self, c):
        raise NotImplementedError(self._is_initialized)

    def _initialize(self, c):
        raise NotImplementedError(self._initialize)

    def _get_auth(self):
        self._url, self._auth_token = self._connection.get_auth(self._auth_url,
                                                                self._user,
                                                                self._auth_key)
        return self._url, self.auth_token


class LeapDocument(Document):

    def get_content_encrypted(self):
        """
        Returns document's json serialization encrypted with user's public key.
        """
        # TODO: replace for openpgp encryption with users's pub key.
        return base64.b64encode(self.get_json())

    def set_content_encrypted(self):
        """
        Set document's content based on encrypted version of json string.
        """
        # TODO:
        #   - replace for openpgp decryption using user's priv key.
        #   - raise error if unsuccessful.
        return self.set_json(base64.b64decode(self.get_json()))


class OpenStackSyncTarget(CommonSyncTarget):

    def get_sync_info(self, source_replica_uid):
        raise NotImplementedError(self.get_sync_info)

    def record_sync_info(self, source_replica_uid, source_replica_generation,
                         source_replica_transaction_id):
        raise NotImplementedError(self.record_sync_info)
