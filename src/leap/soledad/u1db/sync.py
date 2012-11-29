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

"""The synchronization utilities for U1DB."""
from itertools import izip

import u1db
from u1db import errors


class Synchronizer(object):
    """Collect the state around synchronizing 2 U1DB replicas.

    Synchronization is bi-directional, in that new items in the source are sent
    to the target, and new items in the target are returned to the source.
    However, it still recognizes that one side is initiating the request. Also,
    at the moment, conflicts are only created in the source.
    """

    def __init__(self, source, sync_target):
        """Create a new Synchronization object.

        :param source: A Database
        :param sync_target: A SyncTarget
        """
        self.source = source
        self.sync_target = sync_target
        self.target_replica_uid = None
        self.num_inserted = 0

    def _insert_doc_from_target(self, doc, replica_gen, trans_id):
        """Try to insert synced document from target.

        Implements TAKE OTHER semantics: any document from the target
        that is in conflict will be taken as the new official value,
        while the current conflicting value will be stored alongside
        as a conflict. In the process indexes will be updated etc.

        :return: None
        """
        # Increases self.num_inserted depending whether the document
        # was effectively inserted.
        state, _ = self.source._put_doc_if_newer(doc, save_conflict=True,
            replica_uid=self.target_replica_uid, replica_gen=replica_gen,
            replica_trans_id=trans_id)
        if state == 'inserted':
            self.num_inserted += 1
        elif state == 'converged':
            # magical convergence
            pass
        elif state == 'superseded':
            # we have something newer, will be taken care of at the next sync
            pass
        else:
            assert state == 'conflicted'
            # The doc was saved as a conflict, so the database was updated
            self.num_inserted += 1

    def _record_sync_info_with_the_target(self, start_generation):
        """Record our new after sync generation with the target if gapless.

        Any documents received from the target will cause the local
        database to increment its generation. We do not want to send
        them back to the target in a future sync. However, there could
        also be concurrent updates from another process doing eg
        'put_doc' while the sync was running. And we do want to
        synchronize those documents.  We can tell if there was a
        concurrent update by comparing our new generation number
        versus the generation we started, and how many documents we
        inserted from the target. If it matches exactly, then we can
        record with the target that they are fully up to date with our
        new generation.
        """
        cur_gen, trans_id = self.source._get_generation_info()
        if (cur_gen == start_generation + self.num_inserted
                and self.num_inserted > 0):
            self.sync_target.record_sync_info(
                self.source._replica_uid, cur_gen, trans_id)

    def sync(self, callback=None, autocreate=False):
        """Synchronize documents between source and target."""
        sync_target = self.sync_target
        # get target identifier, its current generation,
        # and its last-seen database generation for this source
        try:
            (self.target_replica_uid, target_gen, target_trans_id,
             target_my_gen, target_my_trans_id) = sync_target.get_sync_info(
                self.source._replica_uid)
        except errors.DatabaseDoesNotExist:
            if not autocreate:
                raise
            # will try to ask sync_exchange() to create the db
            self.target_replica_uid = None
            target_gen, target_trans_id = 0, ''
            target_my_gen, target_my_trans_id = 0, ''
            def ensure_callback(replica_uid):
                self.target_replica_uid = replica_uid
        else:
            ensure_callback = None
        # validate the generation and transaction id the target knows about us
        self.source.validate_gen_and_trans_id(
            target_my_gen, target_my_trans_id)
        # what's changed since that generation and this current gen
        my_gen, _, changes = self.source.whats_changed(target_my_gen)

        # this source last-seen database generation for the target
        if self.target_replica_uid is None:
            target_last_known_gen, target_last_known_trans_id = 0, ''
        else:
            target_last_known_gen, target_last_known_trans_id = \
            self.source._get_replica_gen_and_trans_id(self.target_replica_uid)
        if not changes and target_last_known_gen == target_gen:
            if target_trans_id != target_last_known_trans_id:
                raise errors.InvalidTransactionId
            return my_gen
        changed_doc_ids = [doc_id for doc_id, _, _ in changes]
        # prepare to send all the changed docs
        docs_to_send = self.source.get_docs(changed_doc_ids,
            check_for_conflicts=False, include_deleted=True)
        # TODO: there must be a way to not iterate twice
        docs_by_generation = zip(
            docs_to_send, (gen for _, gen, _ in changes),
            (trans for _, _, trans in changes))

        # exchange documents and try to insert the returned ones with
        # the target, return target synced-up-to gen
        new_gen, new_trans_id = sync_target.sync_exchange(
            docs_by_generation, self.source._replica_uid,
            target_last_known_gen, target_last_known_trans_id,
            self._insert_doc_from_target, ensure_callback=ensure_callback)
        # record target synced-up-to generation including applying what we sent
        self.source._set_replica_gen_and_trans_id(
            self.target_replica_uid, new_gen, new_trans_id)

        # if gapless record current reached generation with target
        self._record_sync_info_with_the_target(my_gen)

        return my_gen


class SyncExchange(object):
    """Steps and state for carrying through a sync exchange on a target."""

    def __init__(self, db, source_replica_uid, last_known_generation):
        self._db = db
        self.source_replica_uid = source_replica_uid
        self.source_last_known_generation = last_known_generation
        self.seen_ids = {}  # incoming ids not superseded
        self.changes_to_return = None
        self.new_gen = None
        self.new_trans_id = None
        # for tests
        self._incoming_trace = []
        self._trace_hook = None
        self._db._last_exchange_log = {
            'receive': {'docs': self._incoming_trace},
            'return': None
            }

    def _set_trace_hook(self, cb):
        self._trace_hook = cb

    def _trace(self, state):
        if not self._trace_hook:
            return
        self._trace_hook(state)

    def insert_doc_from_source(self, doc, source_gen, trans_id):
        """Try to insert synced document from source.

        Conflicting documents are not inserted but will be sent over
        to the sync source.

        It keeps track of progress by storing the document source
        generation as well.

        The 1st step of a sync exchange is to call this repeatedly to
        try insert all incoming documents from the source.

        :param doc: A Document object.
        :param source_gen: The source generation of doc.
        :return: None
        """
        state, at_gen = self._db._put_doc_if_newer(doc, save_conflict=False,
            replica_uid=self.source_replica_uid, replica_gen=source_gen,
            replica_trans_id=trans_id)
        if state == 'inserted':
            self.seen_ids[doc.doc_id] = at_gen
        elif state == 'converged':
            # magical convergence
            self.seen_ids[doc.doc_id] = at_gen
        elif state == 'superseded':
            # we have something newer that we will return
            pass
        else:
            # conflict that we will returne
            assert state == 'conflicted'
        # for tests
        self._incoming_trace.append((doc.doc_id, doc.rev))
        self._db._last_exchange_log['receive'].update({
            'source_uid': self.source_replica_uid,
            'source_gen': source_gen
            })

    def find_changes_to_return(self):
        """Find changes to return.

        Find changes since last_known_generation in db generation
        order using whats_changed. It excludes documents ids that have
        already been considered (superseded by the sender, etc).

        :return: new_generation - the generation of this database
            which the caller can consider themselves to be synchronized after
            processing the returned documents.
        """
        self._db._last_exchange_log['receive'].update({  # for tests
            'last_known_gen': self.source_last_known_generation
            })
        self._trace('before whats_changed')
        gen, trans_id, changes = self._db.whats_changed(
            self.source_last_known_generation)
        self._trace('after whats_changed')
        self.new_gen = gen
        self.new_trans_id = trans_id
        seen_ids = self.seen_ids
        # changed docs that weren't superseded by or converged with
        self.changes_to_return = [
            (doc_id, gen, trans_id) for (doc_id, gen, trans_id) in changes
            # there was a subsequent update
            if doc_id not in seen_ids or seen_ids.get(doc_id) < gen]
        return self.new_gen

    def return_docs(self, return_doc_cb):
        """Return the changed documents and their last change generation
        repeatedly invoking the callback return_doc_cb.

        The final step of a sync exchange.

        :param: return_doc_cb(doc, gen, trans_id): is a callback
                used to return the documents with their last change generation
                to the target replica.
        :return: None
        """
        changes_to_return = self.changes_to_return
        # return docs, including conflicts
        changed_doc_ids = [doc_id for doc_id, _, _ in changes_to_return]
        self._trace('before get_docs')
        docs = self._db.get_docs(
            changed_doc_ids, check_for_conflicts=False, include_deleted=True)

        docs_by_gen = izip(
            docs, (gen for _, gen, _ in changes_to_return),
            (trans_id for _, _, trans_id in changes_to_return))
        _outgoing_trace = []  # for tests
        for doc, gen, trans_id in docs_by_gen:
            return_doc_cb(doc, gen, trans_id)
            _outgoing_trace.append((doc.doc_id, doc.rev))
        # for tests
        self._db._last_exchange_log['return'] = {
            'docs': _outgoing_trace,
            'last_gen': self.new_gen
            }


class LocalSyncTarget(u1db.SyncTarget):
    """Common sync target implementation logic for all local sync targets."""

    def __init__(self, db):
        self._db = db
        self._trace_hook = None

    def sync_exchange(self, docs_by_generations, source_replica_uid,
                      last_known_generation, last_known_trans_id,
                      return_doc_cb, ensure_callback=None):
        self._db.validate_gen_and_trans_id(
            last_known_generation, last_known_trans_id)
        sync_exch = SyncExchange(
            self._db, source_replica_uid, last_known_generation)
        if self._trace_hook:
            sync_exch._set_trace_hook(self._trace_hook)
        # 1st step: try to insert incoming docs and record progress
        for doc, doc_gen, trans_id in docs_by_generations:
            sync_exch.insert_doc_from_source(doc, doc_gen, trans_id)
        # 2nd step: find changed documents (including conflicts) to return
        new_gen = sync_exch.find_changes_to_return()
        # final step: return docs and record source replica sync point
        sync_exch.return_docs(return_doc_cb)
        return new_gen, sync_exch.new_trans_id

    def _set_trace_hook(self, cb):
        self._trace_hook = cb
