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

"""The in-memory Database class for U1DB."""

try:
    import simplejson as json
except ImportError:
    import json  # noqa

from u1db import (
    Document,
    errors,
    query_parser,
    vectorclock,
    )
from u1db.backends import CommonBackend, CommonSyncTarget


def get_prefix(value):
    key_prefix = '\x01'.join(value)
    return key_prefix.rstrip('*')


class InMemoryDatabase(CommonBackend):
    """A database that only stores the data internally."""

    def __init__(self, replica_uid, document_factory=None):
        self._transaction_log = []
        self._docs = {}
        # Map from doc_id => [(doc_rev, doc)] conflicts beyond 'winner'
        self._conflicts = {}
        self._other_generations = {}
        self._indexes = {}
        self._replica_uid = replica_uid
        self._factory = document_factory or Document

    def _set_replica_uid(self, replica_uid):
        """Force the replica_uid to be set."""
        self._replica_uid = replica_uid

    def set_document_factory(self, factory):
        self._factory = factory

    def close(self):
        # This is a no-op, We don't want to free the data because one client
        # may be closing it, while another wants to inspect the results.
        pass

    def _get_replica_gen_and_trans_id(self, other_replica_uid):
        return self._other_generations.get(other_replica_uid, (0, ''))

    def _set_replica_gen_and_trans_id(self, other_replica_uid,
                                      other_generation, other_transaction_id):
        self._do_set_replica_gen_and_trans_id(
            other_replica_uid, other_generation, other_transaction_id)

    def _do_set_replica_gen_and_trans_id(self, other_replica_uid,
                                         other_generation,
                                         other_transaction_id):
        # TODO: to handle race conditions, we may want to check if the current
        #       value is greater than this new value.
        self._other_generations[other_replica_uid] = (other_generation,
                                                      other_transaction_id)

    def get_sync_target(self):
        return InMemorySyncTarget(self)

    def _get_transaction_log(self):
        # snapshot!
        return self._transaction_log[:]

    def _get_generation(self):
        return len(self._transaction_log)

    def _get_generation_info(self):
        if not self._transaction_log:
            return 0, ''
        return len(self._transaction_log), self._transaction_log[-1][1]

    def _get_trans_id_for_gen(self, generation):
        if generation == 0:
            return ''
        if generation > len(self._transaction_log):
            raise errors.InvalidGeneration
        return self._transaction_log[generation - 1][1]

    def put_doc(self, doc):
        if doc.doc_id is None:
            raise errors.InvalidDocId()
        self._check_doc_id(doc.doc_id)
        self._check_doc_size(doc)
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
        return new_rev

    def _put_and_update_indexes(self, old_doc, doc):
        for index in self._indexes.itervalues():
            if old_doc is not None and not old_doc.is_tombstone():
                index.remove_json(old_doc.doc_id, old_doc.get_json())
            if not doc.is_tombstone():
                index.add_json(doc.doc_id, doc.get_json())
        trans_id = self._allocate_transaction_id()
        self._docs[doc.doc_id] = (doc.rev, doc.get_json())
        self._transaction_log.append((doc.doc_id, trans_id))

    def _get_doc(self, doc_id, check_for_conflicts=False):
        try:
            doc_rev, content = self._docs[doc_id]
        except KeyError:
            return None
        doc = self._factory(doc_id, doc_rev, content)
        if check_for_conflicts:
            doc.has_conflicts = (doc.doc_id in self._conflicts)
        return doc

    def _has_conflicts(self, doc_id):
        return doc_id in self._conflicts

    def get_doc(self, doc_id, include_deleted=False):
        doc = self._get_doc(doc_id, check_for_conflicts=True)
        if doc is None:
            return None
        if doc.is_tombstone() and not include_deleted:
            return None
        return doc

    def get_all_docs(self, include_deleted=False):
        """Return all documents in the database."""
        generation = self._get_generation()
        results = []
        for doc_id, (doc_rev, content) in self._docs.items():
            if content is None and not include_deleted:
                continue
            doc = self._factory(doc_id, doc_rev, content)
            doc.has_conflicts = self._has_conflicts(doc_id)
            results.append(doc)
        return (generation, results)

    def get_doc_conflicts(self, doc_id):
        if doc_id not in self._conflicts:
            return []
        result = [self._get_doc(doc_id)]
        result[0].has_conflicts = True
        result.extend([self._factory(doc_id, rev, content)
                       for rev, content in self._conflicts[doc_id]])
        return result

    def _replace_conflicts(self, doc, conflicts):
        if not conflicts:
            del self._conflicts[doc.doc_id]
        else:
            self._conflicts[doc.doc_id] = conflicts
        doc.has_conflicts = bool(conflicts)

    def _prune_conflicts(self, doc, doc_vcr):
        if self._has_conflicts(doc.doc_id):
            autoresolved = False
            remaining_conflicts = []
            cur_conflicts = self._conflicts[doc.doc_id]
            for c_rev, c_doc in cur_conflicts:
                c_vcr = vectorclock.VectorClockRev(c_rev)
                if doc_vcr.is_newer(c_vcr):
                    continue
                if doc.same_content_as(Document(doc.doc_id, c_rev, c_doc)):
                    doc_vcr.maximize(c_vcr)
                    autoresolved = True
                    continue
                remaining_conflicts.append((c_rev, c_doc))
            if autoresolved:
                doc_vcr.increment(self._replica_uid)
                doc.rev = doc_vcr.as_str()
            self._replace_conflicts(doc, remaining_conflicts)

    def resolve_doc(self, doc, conflicted_doc_revs):
        cur_doc = self._get_doc(doc.doc_id)
        if cur_doc is None:
            cur_rev = None
        else:
            cur_rev = cur_doc.rev
        new_rev = self._ensure_maximal_rev(cur_rev, conflicted_doc_revs)
        superseded_revs = set(conflicted_doc_revs)
        remaining_conflicts = []
        cur_conflicts = self._conflicts[doc.doc_id]
        for c_rev, c_doc in cur_conflicts:
            if c_rev in superseded_revs:
                continue
            remaining_conflicts.append((c_rev, c_doc))
        doc.rev = new_rev
        if cur_rev in superseded_revs:
            self._put_and_update_indexes(cur_doc, doc)
        else:
            remaining_conflicts.append((new_rev, doc.get_json()))
        self._replace_conflicts(doc, remaining_conflicts)

    def delete_doc(self, doc):
        if doc.doc_id not in self._docs:
            raise errors.DocumentDoesNotExist
        if self._docs[doc.doc_id][1] in ('null', None):
            raise errors.DocumentAlreadyDeleted
        doc.make_tombstone()
        self.put_doc(doc)

    def create_index(self, index_name, *index_expressions):
        if index_name in self._indexes:
            if self._indexes[index_name]._definition == list(
                    index_expressions):
                return
            raise errors.IndexNameTakenError
        index = InMemoryIndex(index_name, list(index_expressions))
        for doc_id, (doc_rev, doc) in self._docs.iteritems():
            if doc is not None:
                index.add_json(doc_id, doc)
        self._indexes[index_name] = index

    def delete_index(self, index_name):
        del self._indexes[index_name]

    def list_indexes(self):
        definitions = []
        for idx in self._indexes.itervalues():
            definitions.append((idx._name, idx._definition))
        return definitions

    def get_from_index(self, index_name, *key_values):
        try:
            index = self._indexes[index_name]
        except KeyError:
            raise errors.IndexDoesNotExist
        doc_ids = index.lookup(key_values)
        result = []
        for doc_id in doc_ids:
            result.append(self._get_doc(doc_id, check_for_conflicts=True))
        return result

    def get_range_from_index(self, index_name, start_value=None,
                             end_value=None):
        """Return all documents with key values in the specified range."""
        try:
            index = self._indexes[index_name]
        except KeyError:
            raise errors.IndexDoesNotExist
        if isinstance(start_value, basestring):
            start_value = (start_value,)
        if isinstance(end_value, basestring):
            end_value = (end_value,)
        doc_ids = index.lookup_range(start_value, end_value)
        result = []
        for doc_id in doc_ids:
            result.append(self._get_doc(doc_id, check_for_conflicts=True))
        return result

    def get_index_keys(self, index_name):
        try:
            index = self._indexes[index_name]
        except KeyError:
            raise errors.IndexDoesNotExist
        keys = index.keys()
        # XXX inefficiency warning
        return list(set([tuple(key.split('\x01')) for key in keys]))

    def whats_changed(self, old_generation=0):
        changes = []
        relevant_tail = self._transaction_log[old_generation:]
        # We don't use len(self._transaction_log) because _transaction_log may
        # get mutated by a concurrent operation.
        cur_generation = old_generation + len(relevant_tail)
        last_trans_id = ''
        if relevant_tail:
            last_trans_id = relevant_tail[-1][1]
        elif self._transaction_log:
            last_trans_id = self._transaction_log[-1][1]
        seen = set()
        generation = cur_generation
        for doc_id, trans_id in reversed(relevant_tail):
            if doc_id not in seen:
                changes.append((doc_id, generation, trans_id))
                seen.add(doc_id)
            generation -= 1
        changes.reverse()
        return (cur_generation, last_trans_id, changes)

    def _force_doc_sync_conflict(self, doc):
        my_doc = self._get_doc(doc.doc_id)
        self._prune_conflicts(doc, vectorclock.VectorClockRev(doc.rev))
        self._conflicts.setdefault(doc.doc_id, []).append(
            (my_doc.rev, my_doc.get_json()))
        doc.has_conflicts = True
        self._put_and_update_indexes(my_doc, doc)


class InMemoryIndex(object):
    """Interface for managing an Index."""

    def __init__(self, index_name, index_definition):
        self._name = index_name
        self._definition = index_definition
        self._values = {}
        parser = query_parser.Parser()
        self._getters = parser.parse_all(self._definition)

    def evaluate_json(self, doc):
        """Determine the 'key' after applying this index to the doc."""
        raw = json.loads(doc)
        return self.evaluate(raw)

    def evaluate(self, obj):
        """Evaluate a dict object, applying this definition."""
        all_rows = [[]]
        for getter in self._getters:
            new_rows = []
            keys = getter.get(obj)
            if not keys:
                return []
            for key in keys:
                new_rows.extend([row + [key] for row in all_rows])
            all_rows = new_rows
        all_rows = ['\x01'.join(row) for row in all_rows]
        return all_rows

    def add_json(self, doc_id, doc):
        """Add this json doc to the index."""
        keys = self.evaluate_json(doc)
        if not keys:
            return
        for key in keys:
            self._values.setdefault(key, []).append(doc_id)

    def remove_json(self, doc_id, doc):
        """Remove this json doc from the index."""
        keys = self.evaluate_json(doc)
        if keys:
            for key in keys:
                doc_ids = self._values[key]
                doc_ids.remove(doc_id)
                if not doc_ids:
                    del self._values[key]

    def _find_non_wildcards(self, values):
        """Check if this should be a wildcard match.

        Further, this will raise an exception if the syntax is improperly
        defined.

        :return: The offset of the last value we need to match against.
        """
        if len(values) != len(self._definition):
            raise errors.InvalidValueForIndex()
        is_wildcard = False
        last = 0
        for idx, val in enumerate(values):
            if val.endswith('*'):
                if val != '*':
                    # We have an 'x*' style wildcard
                    if is_wildcard:
                        # We were already in wildcard mode, so this is invalid
                        raise errors.InvalidGlobbing
                    last = idx + 1
                is_wildcard = True
            else:
                if is_wildcard:
                    # We were in wildcard mode, we can't follow that with
                    # non-wildcard
                    raise errors.InvalidGlobbing
                last = idx + 1
        if not is_wildcard:
            return -1
        return last

    def lookup(self, values):
        """Find docs that match the values."""
        last = self._find_non_wildcards(values)
        if last == -1:
            return self._lookup_exact(values)
        else:
            return self._lookup_prefix(values[:last])

    def lookup_range(self, start_values, end_values):
        """Find docs within the range."""
        # TODO: Wildly inefficient, which is unlikely to be a problem for the
        # inmemory implementation.
        if start_values:
            self._find_non_wildcards(start_values)
            start_values = get_prefix(start_values)
        if end_values:
            if self._find_non_wildcards(end_values) == -1:
                exact = True
            else:
                exact = False
            end_values = get_prefix(end_values)
        found = []
        for key, doc_ids in sorted(self._values.iteritems()):
            if start_values and start_values > key:
                continue
            if end_values and end_values < key:
                if exact:
                    break
                else:
                    if not key.startswith(end_values):
                        break
            found.extend(doc_ids)
        return found

    def keys(self):
        """Find the indexed keys."""
        return self._values.keys()

    def _lookup_prefix(self, value):
        """Find docs that match the prefix string in values."""
        # TODO: We need a different data structure to make prefix style fast,
        #       some sort of sorted list would work, but a plain dict doesn't.
        key_prefix = get_prefix(value)
        all_doc_ids = []
        for key, doc_ids in sorted(self._values.iteritems()):
            if key.startswith(key_prefix):
                all_doc_ids.extend(doc_ids)
        return all_doc_ids

    def _lookup_exact(self, value):
        """Find docs that match exactly."""
        key = '\x01'.join(value)
        if key in self._values:
            return self._values[key]
        return ()


class InMemorySyncTarget(CommonSyncTarget):

    def get_sync_info(self, source_replica_uid):
        source_gen, source_trans_id = self._db._get_replica_gen_and_trans_id(
            source_replica_uid)
        my_gen, my_trans_id = self._db._get_generation_info()
        return (
            self._db._replica_uid, my_gen, my_trans_id, source_gen,
            source_trans_id)

    def record_sync_info(self, source_replica_uid, source_replica_generation,
                         source_transaction_id):
        if self._trace_hook:
            self._trace_hook('record_sync_info')
        self._db._set_replica_gen_and_trans_id(
            source_replica_uid, source_replica_generation,
            source_transaction_id)
