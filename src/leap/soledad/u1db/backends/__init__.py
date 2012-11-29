# Copyright 2011 Canonical Ltd.
#
# This file is part of u1db.
#
# u1db is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# u1db is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with u1db.  If not, see <http://www.gnu.org/licenses/>.

"""Abstract classes and common implementations for the backends."""

import re
try:
    import simplejson as json
except ImportError:
    import json  # noqa
import uuid

import u1db
from u1db import (
    errors,
)
import u1db.sync
from u1db.vectorclock import VectorClockRev


check_doc_id_re = re.compile("^" + u1db.DOC_ID_CONSTRAINTS + "$", re.UNICODE)


class CommonSyncTarget(u1db.sync.LocalSyncTarget):
    pass


class CommonBackend(u1db.Database):

    document_size_limit = 0

    def _allocate_doc_id(self):
        """Generate a unique identifier for this document."""
        return 'D-' + uuid.uuid4().hex  # 'D-' stands for document

    def _allocate_transaction_id(self):
        return 'T-' + uuid.uuid4().hex  # 'T-' stands for transaction

    def _allocate_doc_rev(self, old_doc_rev):
        vcr = VectorClockRev(old_doc_rev)
        vcr.increment(self._replica_uid)
        return vcr.as_str()

    def _check_doc_id(self, doc_id):
        if not check_doc_id_re.match(doc_id):
            raise errors.InvalidDocId()

    def _check_doc_size(self, doc):
        if not self.document_size_limit:
            return
        if doc.get_size() > self.document_size_limit:
            raise errors.DocumentTooBig

    def _get_generation(self):
        """Return the current generation.

        """
        raise NotImplementedError(self._get_generation)

    def _get_generation_info(self):
        """Return the current generation and transaction id.

        """
        raise NotImplementedError(self._get_generation_info)

    def _get_doc(self, doc_id, check_for_conflicts=False):
        """Extract the document from storage.

        This can return None if the document doesn't exist.
        """
        raise NotImplementedError(self._get_doc)

    def _has_conflicts(self, doc_id):
        """Return True if the doc has conflicts, False otherwise."""
        raise NotImplementedError(self._has_conflicts)

    def create_doc(self, content, doc_id=None):
        json_string = json.dumps(content)
        if doc_id is None:
            doc_id = self._allocate_doc_id()
        doc = self._factory(doc_id, None, json_string)
        self.put_doc(doc)
        return doc

    def create_doc_from_json(self, json, doc_id=None):
        if doc_id is None:
            doc_id = self._allocate_doc_id()
        doc = self._factory(doc_id, None, json)
        self.put_doc(doc)
        return doc

    def _get_transaction_log(self):
        """This is only for the test suite, it is not part of the api."""
        raise NotImplementedError(self._get_transaction_log)

    def _put_and_update_indexes(self, doc_id, old_doc, new_rev, content):
        raise NotImplementedError(self._put_and_update_indexes)

    def get_docs(self, doc_ids, check_for_conflicts=True,
                 include_deleted=False):
        for doc_id in doc_ids:
            doc = self._get_doc(
                doc_id, check_for_conflicts=check_for_conflicts)
            if doc.is_tombstone() and not include_deleted:
                continue
            yield doc

    def _get_trans_id_for_gen(self, generation):
        """Get the transaction id corresponding to a particular generation.

        Raises an InvalidGeneration when the generation does not exist.

        """
        raise NotImplementedError(self._get_trans_id_for_gen)

    def validate_gen_and_trans_id(self, generation, trans_id):
        """Validate the generation and transaction id.

        Raises an InvalidGeneration when the generation does not exist, and an
        InvalidTransactionId when it does but with a different transaction id.

        """
        if generation == 0:
            return
        known_trans_id = self._get_trans_id_for_gen(generation)
        if known_trans_id != trans_id:
            raise errors.InvalidTransactionId

    def _validate_source(self, other_replica_uid, other_generation,
                         other_transaction_id):
        """Validate the new generation and transaction id.

        other_generation must be greater than what we have stored for this
        replica, *or* it must be the same and the transaction_id must be the
        same as well.
        """
        (old_generation,
         old_transaction_id) = self._get_replica_gen_and_trans_id(
             other_replica_uid)
        if other_generation < old_generation:
            raise errors.InvalidGeneration
        if other_generation > old_generation:
            return
        if other_transaction_id == old_transaction_id:
            return
        raise errors.InvalidTransactionId

    def _put_doc_if_newer(self, doc, save_conflict, replica_uid, replica_gen,
                          replica_trans_id=''):
        cur_doc = self._get_doc(doc.doc_id)
        doc_vcr = VectorClockRev(doc.rev)
        if cur_doc is None:
            cur_vcr = VectorClockRev(None)
        else:
            cur_vcr = VectorClockRev(cur_doc.rev)
        self._validate_source(replica_uid, replica_gen, replica_trans_id)
        if doc_vcr.is_newer(cur_vcr):
            rev = doc.rev
            self._prune_conflicts(doc, doc_vcr)
            if doc.rev != rev:
                # conflicts have been autoresolved
                state = 'superseded'
            else:
                state = 'inserted'
            self._put_and_update_indexes(cur_doc, doc)
        elif doc.rev == cur_doc.rev:
            # magical convergence
            state = 'converged'
        elif cur_vcr.is_newer(doc_vcr):
            # Don't add this to seen_ids, because we have something newer,
            # so we should send it back, and we should not generate a
            # conflict
            state = 'superseded'
        elif cur_doc.same_content_as(doc):
            # the documents have been edited to the same thing at both ends
            doc_vcr.maximize(cur_vcr)
            doc_vcr.increment(self._replica_uid)
            doc.rev = doc_vcr.as_str()
            self._put_and_update_indexes(cur_doc, doc)
            state = 'superseded'
        else:
            state = 'conflicted'
            if save_conflict:
                self._force_doc_sync_conflict(doc)
        if replica_uid is not None and replica_gen is not None:
            self._do_set_replica_gen_and_trans_id(
                replica_uid, replica_gen, replica_trans_id)
        return state, self._get_generation()

    def _ensure_maximal_rev(self, cur_rev, extra_revs):
        vcr = VectorClockRev(cur_rev)
        for rev in extra_revs:
            vcr.maximize(VectorClockRev(rev))
        vcr.increment(self._replica_uid)
        return vcr.as_str()

    def set_document_size_limit(self, limit):
        self.document_size_limit = limit
