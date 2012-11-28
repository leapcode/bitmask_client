# License?

"""A U1DB implementation that uses OpenStack Swift as its persistence layer."""

import errno
import os
try:
    import simplejson as json
except ImportError:
    import json  # noqa
import sys
import time
import uuid

from u1db.backends import CommonBackend, CommonSyncTarget
from u1db import (
    Document,
    errors,
    query_parser,
    vectorclock,
    )


class OpenStackDatabase(CommonBackend):
    """A U1DB implementation that uses OpenStack as its persistence layer."""

    def __init__(self, sqlite_file, document_factory=None):
        """Create a new OpenStack data container."""
        raise NotImplementedError(self.__init__)

    def set_document_factory(self, factory):
        self._factory = factory

    def get_sync_target(self):
        return OpenStackSyncTarget(self)

    @classmethod
    def open_database(cls, sqlite_file, create, backend_cls=None,
                      document_factory=None):
        raise NotImplementedError(open_database)

    @staticmethod
    def delete_database(sqlite_file):
        raise NotImplementedError(delete_database)


    def close(self):
        raise NotImplementedError(self.close)

    def _is_initialized(self, c):
        raise NotImplementedError(self._is_initialized)

    def _initialize(self, c):
        raise NotImplementedError(self._initialize)

    def _ensure_schema(self):
        raise NotImplementedError(self._ensure_schema)

    def _set_replica_uid(self, replica_uid):
        """Force the replica_uid to be set."""
        raise NotImplementedError(self._set_replica_uid)

    def _set_replica_uid_in_transaction(self, replica_uid):
        """Set the replica_uid. A transaction should already be held."""
        raise NotImplementedError(self._set_replica_uid_in_transaction)

    def _get_replica_uid(self):
        raise NotImplementedError(self._get_replica_uid)

    _replica_uid = property(_get_replica_uid)

    def _get_generation(self):
        raise NotImplementedError(self._get_generation)

    def _get_generation_info(self):
        raise NotImplementedError(self._get_generation_info)

    def _get_trans_id_for_gen(self, generation):
        raise NotImplementedError(self._get_trans_id_for_gen)

    def _get_transaction_log(self):
        raise NotImplementedError(self._get_transaction_log)

    def _get_doc(self, doc_id, check_for_conflicts=False):
        """Get just the document content, without fancy handling."""
        raise NotImplementedError(self._get_doc)

    def _has_conflicts(self, doc_id):
        raise NotImplementedError(self._has_conflicts)

    def get_doc(self, doc_id, include_deleted=False):
        raise NotImplementedError(self.get_doc)

    def get_all_docs(self, include_deleted=False):
        """Get all documents from the database."""
        raise NotImplementedError(self.get_all_docs)

    def put_doc(self, doc):
        raise NotImplementedError(self.put_doc)

    def whats_changed(self, old_generation=0):
        raise NotImplementedError(self.whats_changed)

    def delete_doc(self, doc):
        raise NotImplementedError(self.delete_doc)

    def _get_conflicts(self, doc_id):
        return []

    def get_doc_conflicts(self, doc_id):
        return []

    def _get_replica_gen_and_trans_id(self, other_replica_uid):
        raise NotImplementedError(self._get_replica_gen_and_trans_id)

    def _set_replica_gen_and_trans_id(self, other_replica_uid,
                                      other_generation, other_transaction_id):
        raise NotImplementedError(self._set_replica_gen_and_trans_id)

    def _do_set_replica_gen_and_trans_id(self, other_replica_uid,
                                         other_generation,
                                         other_transaction_id):
        raise NotImplementedError(self._do_set_replica_gen_and_trans_id)

    def _put_doc_if_newer(self, doc, save_conflict, replica_uid=None,
                          replica_gen=None, replica_trans_id=None):
        raise NotImplementedError(self._put_doc_if_newer)

    def resolve_doc(self, doc, conflicted_doc_revs):
        raise NotImplementedError(self.resolve_doc)

    def list_indexes(self):
        return []

    def get_from_index(self, index_name, *key_values):
        return []

    def get_range_from_index(self, index_name, start_value=None,
                             end_value=None):
        return []

    def get_index_keys(self, index_name):
        return []

    def delete_index(self, index_name):
        return False

class LeapDocument(Document):

    def get_content_encrypted(self):
        raise NotImplementedError(self.get_content_encrypted)

    def set_content_encrypted(self):
        raise NotImplementedError(self.set_content_encrypted)


class OpenStackSyncTarget(CommonSyncTarget):

    def get_sync_info(self, source_replica_uid):
        raise NotImplementedError(self.get_sync_info)

    def record_sync_info(self, source_replica_uid, source_replica_generation,
                         source_replica_transaction_id):
        raise NotImplementedError(self.record_sync_info)
