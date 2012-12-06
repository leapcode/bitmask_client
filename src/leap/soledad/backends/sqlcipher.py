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

"""A U1DB implementation that uses SQLCipher as its persistence layer."""

import errno
import os
try:
    import simplejson as json
except ImportError:
    import json  # noqa
from sqlite3 import dbapi2
import sys
import time
import uuid

import pkg_resources

from u1db.backends import CommonBackend, CommonSyncTarget
from u1db import (
    Document,
    errors,
    query_parser,
    vectorclock,
    )


def open(path, create, document_factory=None, password=None):
    """Open a database at the given location.

    Will raise u1db.errors.DatabaseDoesNotExist if create=False and the
    database does not already exist.

    :param path: The filesystem path for the database to open.
    :param create: True/False, should the database be created if it doesn't
        already exist?
    :param document_factory: A function that will be called with the same
        parameters as Document.__init__.
    :return: An instance of Database.
    """
    from u1db.backends import sqlite_backend
    return sqlite_backend.SQLCipherDatabase.open_database(
        path, create=create, document_factory=document_factory, password=password)


class SQLCipherDatabase(CommonBackend):
    """A U1DB implementation that uses SQLCipher as its persistence layer."""

    _sqlite_registry = {}

    @classmethod
    def set_pragma_key(cls, db_handle, key):
       db_handle.cursor().execute("PRAGMA key = '%s'" % key)

    def __init__(self, sqlite_file, document_factory=None, password=None):
        """Create a new sqlite file."""
        self._db_handle = dbapi2.connect(sqlite_file)
        if password:
            SQLiteDatabase.set_pragma_key(self._db_handle, password)
        self._real_replica_uid = None
        self._ensure_schema()
        self._factory = document_factory or Document

    def set_document_factory(self, factory):
        self._factory = factory

    def get_sync_target(self):
        return SQLCipherSyncTarget(self)

    @classmethod
    def _which_index_storage(cls, c):
        try:
            c.execute("SELECT value FROM u1db_config"
                      " WHERE name = 'index_storage'")
        except dbapi2.OperationalError, e:
            # The table does not exist yet
            return None, e
        else:
            return c.fetchone()[0], None

    WAIT_FOR_PARALLEL_INIT_HALF_INTERVAL = 0.5

    @classmethod
    def _open_database(cls, sqlite_file, document_factory=None, password=None):
        if not os.path.isfile(sqlite_file):
            raise errors.DatabaseDoesNotExist()
        tries = 2
        while True:
            # Note: There seems to be a bug in sqlite 3.5.9 (with python2.6)
            #       where without re-opening the database on Windows, it
            #       doesn't see the transaction that was just committed
            db_handle = dbapi2.connect(sqlite_file)
            if password:
                SQLiteDatabase.set_pragma_key(db_handle, password)
            c = db_handle.cursor()
            v, err = cls._which_index_storage(c)
            db_handle.close()
            if v is not None:
                break
            # possibly another process is initializing it, wait for it to be
            # done
            if tries == 0:
                raise err  # go for the richest error?
            tries -= 1
            time.sleep(cls.WAIT_FOR_PARALLEL_INIT_HALF_INTERVAL)
        return SQLCipherDatabase._sqlite_registry[v](
            sqlite_file, document_factory=document_factory)

    @classmethod
    def open_database(cls, sqlite_file, create, backend_cls=None,
                      document_factory=None, password=None):
        try:
            return cls._open_database(sqlite_file,
                                      document_factory=document_factory,
                                      password=password)
        except errors.DatabaseDoesNotExist:
            if not create:
                raise
            if backend_cls is None:
                # default is SQLCipherPartialExpandDatabase
                backend_cls = SQLCipherPartialExpandDatabase
            return backend_cls(sqlite_file, document_factory=document_factory,
                               password=password)

    @staticmethod
    def delete_database(sqlite_file):
        try:
            os.unlink(sqlite_file)
        except OSError as ex:
            if ex.errno == errno.ENOENT:
                raise errors.DatabaseDoesNotExist()
            raise

    @staticmethod
    def register_implementation(klass):
        """Register that we implement an SQLCipherDatabase.

        The attribute _index_storage_value will be used as the lookup key.
        """
        SQLCipherDatabase._sqlite_registry[klass._index_storage_value] = klass

    def _get_sqlite_handle(self):
        """Get access to the underlying sqlite database.

        This should only be used by the test suite, etc, for examining the
        state of the underlying database.
        """
        return self._db_handle

    def _close_sqlite_handle(self):
        """Release access to the underlying sqlite database."""
        self._db_handle.close()

    def close(self):
        self._close_sqlite_handle()

    def _is_initialized(self, c):
        """Check if this database has been initialized."""
        c.execute("PRAGMA case_sensitive_like=ON")
        try:
            c.execute("SELECT value FROM u1db_config"
                      " WHERE name = 'sql_schema'")
        except dbapi2.OperationalError:
            # The table does not exist yet
            val = None
        else:
            val = c.fetchone()
        if val is not None:
            return True
        return False

    def _initialize(self, c):
        """Create the schema in the database."""
        #read the script with sql commands
        # TODO: Change how we set up the dependency. Most likely use something
        #   like lp:dirspec to grab the file from a common resource
        #   directory. Doesn't specifically need to be handled until we get
        #   to the point of packaging this.
        schema_content = pkg_resources.resource_string(
            __name__, 'dbschema.sql')
        # Note: We'd like to use c.executescript() here, but it seems that
        #       executescript always commits, even if you set
        #       isolation_level = None, so if we want to properly handle
        #       exclusive locking and rollbacks between processes, we need
        #       to execute it line-by-line
        for line in schema_content.split(';'):
            if not line:
                continue
            c.execute(line)
        #add extra fields
        self._extra_schema_init(c)
        # A unique identifier should be set for this replica. Implementations
        # don't have to strictly use uuid here, but we do want the uid to be
        # unique amongst all databases that will sync with each other.
        # We might extend this to using something with hostname for easier
        # debugging.
        self._set_replica_uid_in_transaction(uuid.uuid4().hex)
        c.execute("INSERT INTO u1db_config VALUES" " ('index_storage', ?)",
                  (self._index_storage_value,))

    def _ensure_schema(self):
        """Ensure that the database schema has been created."""
        old_isolation_level = self._db_handle.isolation_level
        c = self._db_handle.cursor()
        if self._is_initialized(c):
            return
        try:
            # autocommit/own mgmt of transactions
            self._db_handle.isolation_level = None
            with self._db_handle:
                # only one execution path should initialize the db
                c.execute("begin exclusive")
                if self._is_initialized(c):
                    return
                self._initialize(c)
        finally:
            self._db_handle.isolation_level = old_isolation_level

    def _extra_schema_init(self, c):
        """Add any extra fields, etc to the basic table definitions."""

    def _parse_index_definition(self, index_field):
        """Parse a field definition for an index, returning a Getter."""
        # Note: We may want to keep a Parser object around, and cache the
        #       Getter objects for a greater length of time. Specifically, if
        #       you create a bunch of indexes, and then insert 50k docs, you'll
        #       re-parse the indexes between puts. The time to insert the docs
        #       is still likely to dominate put_doc time, though.
        parser = query_parser.Parser()
        getter = parser.parse(index_field)
        return getter

    def _update_indexes(self, doc_id, raw_doc, getters, db_cursor):
        """Update document_fields for a single document.

        :param doc_id: Identifier for this document
        :param raw_doc: The python dict representation of the document.
        :param getters: A list of [(field_name, Getter)]. Getter.get will be
            called to evaluate the index definition for this document, and the
            results will be inserted into the db.
        :param db_cursor: An sqlite Cursor.
        :return: None
        """
        values = []
        for field_name, getter in getters:
            for idx_value in getter.get(raw_doc):
                values.append((doc_id, field_name, idx_value))
        if values:
            db_cursor.executemany(
                "INSERT INTO document_fields VALUES (?, ?, ?)", values)

    def _set_replica_uid(self, replica_uid):
        """Force the replica_uid to be set."""
        with self._db_handle:
            self._set_replica_uid_in_transaction(replica_uid)

    def _set_replica_uid_in_transaction(self, replica_uid):
        """Set the replica_uid. A transaction should already be held."""
        c = self._db_handle.cursor()
        c.execute("INSERT OR REPLACE INTO u1db_config"
                  " VALUES ('replica_uid', ?)",
                  (replica_uid,))
        self._real_replica_uid = replica_uid

    def _get_replica_uid(self):
        if self._real_replica_uid is not None:
            return self._real_replica_uid
        c = self._db_handle.cursor()
        c.execute("SELECT value FROM u1db_config WHERE name = 'replica_uid'")
        val = c.fetchone()
        if val is None:
            return None
        self._real_replica_uid = val[0]
        return self._real_replica_uid

    _replica_uid = property(_get_replica_uid)

    def _get_generation(self):
        c = self._db_handle.cursor()
        c.execute('SELECT max(generation) FROM transaction_log')
        val = c.fetchone()[0]
        if val is None:
            return 0
        return val

    def _get_generation_info(self):
        c = self._db_handle.cursor()
        c.execute(
            'SELECT max(generation), transaction_id FROM transaction_log ')
        val = c.fetchone()
        if val[0] is None:
            return(0, '')
        return val

    def _get_trans_id_for_gen(self, generation):
        if generation == 0:
            return ''
        c = self._db_handle.cursor()
        c.execute(
            'SELECT transaction_id FROM transaction_log WHERE generation = ?',
            (generation,))
        val = c.fetchone()
        if val is None:
            raise errors.InvalidGeneration
        return val[0]

    def _get_transaction_log(self):
        c = self._db_handle.cursor()
        c.execute("SELECT doc_id, transaction_id FROM transaction_log"
                  " ORDER BY generation")
        return c.fetchall()

    def _get_doc(self, doc_id, check_for_conflicts=False):
        """Get just the document content, without fancy handling."""
        c = self._db_handle.cursor()
        if check_for_conflicts:
            c.execute(
                "SELECT document.doc_rev, document.content, "
                "count(conflicts.doc_rev) FROM document LEFT OUTER JOIN "
                "conflicts ON conflicts.doc_id = document.doc_id WHERE "
                "document.doc_id = ? GROUP BY document.doc_id, "
                "document.doc_rev, document.content;", (doc_id,))
        else:
            c.execute(
                "SELECT doc_rev, content, 0 FROM document WHERE doc_id = ?",
                (doc_id,))
        val = c.fetchone()
        if val is None:
            return None
        doc_rev, content, conflicts = val
        doc = self._factory(doc_id, doc_rev, content)
        doc.has_conflicts = conflicts > 0
        return doc

    def _has_conflicts(self, doc_id):
        c = self._db_handle.cursor()
        c.execute("SELECT 1 FROM conflicts WHERE doc_id = ? LIMIT 1",
                  (doc_id,))
        val = c.fetchone()
        if val is None:
            return False
        else:
            return True

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
        c = self._db_handle.cursor()
        c.execute(
            "SELECT document.doc_id, document.doc_rev, document.content, "
            "count(conflicts.doc_rev) FROM document LEFT OUTER JOIN conflicts "
            "ON conflicts.doc_id = document.doc_id GROUP BY document.doc_id, "
            "document.doc_rev, document.content;")
        rows = c.fetchall()
        for doc_id, doc_rev, content, conflicts in rows:
            if content is None and not include_deleted:
                continue
            doc = self._factory(doc_id, doc_rev, content)
            doc.has_conflicts = conflicts > 0
            results.append(doc)
        return (generation, results)

    def put_doc(self, doc):
        if doc.doc_id is None:
            raise errors.InvalidDocId()
        self._check_doc_id(doc.doc_id)
        self._check_doc_size(doc)
        with self._db_handle:
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

    def _expand_to_fields(self, doc_id, base_field, raw_doc, save_none):
        """Convert a dict representation into named fields.

        So something like: {'key1': 'val1', 'key2': 'val2'}
        gets converted into: [(doc_id, 'key1', 'val1', 0)
                              (doc_id, 'key2', 'val2', 0)]
        :param doc_id: Just added to every record.
        :param base_field: if set, these are nested keys, so each field should
            be appropriately prefixed.
        :param raw_doc: The python dictionary.
        """
        # TODO: Handle lists
        values = []
        for field_name, value in raw_doc.iteritems():
            if value is None and not save_none:
                continue
            if base_field:
                full_name = base_field + '.' + field_name
            else:
                full_name = field_name
            if value is None or isinstance(value, (int, float, basestring)):
                values.append((doc_id, full_name, value, len(values)))
            else:
                subvalues = self._expand_to_fields(doc_id, full_name, value,
                                                   save_none)
                for _, subfield_name, val, _ in subvalues:
                    values.append((doc_id, subfield_name, val, len(values)))
        return values

    def _put_and_update_indexes(self, old_doc, doc):
        """Actually insert a document into the database.

        This both updates the existing documents content, and any indexes that
        refer to this document.
        """
        raise NotImplementedError(self._put_and_update_indexes)

    def whats_changed(self, old_generation=0):
        c = self._db_handle.cursor()
        c.execute("SELECT generation, doc_id, transaction_id"
                  " FROM transaction_log"
                  " WHERE generation > ? ORDER BY generation DESC",
                  (old_generation,))
        results = c.fetchall()
        cur_gen = old_generation
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
            c.execute("SELECT generation, transaction_id"
                      " FROM transaction_log ORDER BY generation DESC LIMIT 1")
            results = c.fetchone()
            if not results:
                cur_gen = 0
                newest_trans_id = ''
            else:
                cur_gen, newest_trans_id = results

        return cur_gen, newest_trans_id, changes

    def delete_doc(self, doc):
        with self._db_handle:
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

    def _get_conflicts(self, doc_id):
        c = self._db_handle.cursor()
        c.execute("SELECT doc_rev, content FROM conflicts WHERE doc_id = ?",
                  (doc_id,))
        return [self._factory(doc_id, doc_rev, content)
                for doc_rev, content in c.fetchall()]

    def get_doc_conflicts(self, doc_id):
        with self._db_handle:
            conflict_docs = self._get_conflicts(doc_id)
            if not conflict_docs:
                return []
            this_doc = self._get_doc(doc_id)
            this_doc.has_conflicts = True
            return [this_doc] + conflict_docs

    def _get_replica_gen_and_trans_id(self, other_replica_uid):
        c = self._db_handle.cursor()
        c.execute("SELECT known_generation, known_transaction_id FROM sync_log"
                  " WHERE replica_uid = ?",
                  (other_replica_uid,))
        val = c.fetchone()
        if val is None:
            other_gen = 0
            trans_id = ''
        else:
            other_gen = val[0]
            trans_id = val[1]
        return other_gen, trans_id

    def _set_replica_gen_and_trans_id(self, other_replica_uid,
                                      other_generation, other_transaction_id):
        with self._db_handle:
            self._do_set_replica_gen_and_trans_id(
                other_replica_uid, other_generation, other_transaction_id)

    def _do_set_replica_gen_and_trans_id(self, other_replica_uid,
                                         other_generation,
                                         other_transaction_id):
            c = self._db_handle.cursor()
            c.execute("INSERT OR REPLACE INTO sync_log VALUES (?, ?, ?)",
                      (other_replica_uid, other_generation,
                       other_transaction_id))

    def _put_doc_if_newer(self, doc, save_conflict, replica_uid=None,
                          replica_gen=None, replica_trans_id=None):
        with self._db_handle:
            return super(SQLCipherDatabase, self)._put_doc_if_newer(doc,
                save_conflict=save_conflict,
                replica_uid=replica_uid, replica_gen=replica_gen,
                replica_trans_id=replica_trans_id)

    def _add_conflict(self, c, doc_id, my_doc_rev, my_content):
        c.execute("INSERT INTO conflicts VALUES (?, ?, ?)",
                  (doc_id, my_doc_rev, my_content))

    def _delete_conflicts(self, c, doc, conflict_revs):
        deleting = [(doc.doc_id, c_rev) for c_rev in conflict_revs]
        c.executemany("DELETE FROM conflicts"
                      " WHERE doc_id=? AND doc_rev=?", deleting)
        doc.has_conflicts = self._has_conflicts(doc.doc_id)

    def _prune_conflicts(self, doc, doc_vcr):
        if self._has_conflicts(doc.doc_id):
            autoresolved = False
            c_revs_to_prune = []
            for c_doc in self._get_conflicts(doc.doc_id):
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
            c = self._db_handle.cursor()
            self._delete_conflicts(c, doc, c_revs_to_prune)

    def _force_doc_sync_conflict(self, doc):
        my_doc = self._get_doc(doc.doc_id)
        c = self._db_handle.cursor()
        self._prune_conflicts(doc, vectorclock.VectorClockRev(doc.rev))
        self._add_conflict(c, doc.doc_id, my_doc.rev, my_doc.get_json())
        doc.has_conflicts = True
        self._put_and_update_indexes(my_doc, doc)

    def resolve_doc(self, doc, conflicted_doc_revs):
        with self._db_handle:
            cur_doc = self._get_doc(doc.doc_id)
            # TODO: https://bugs.launchpad.net/u1db/+bug/928274
            #       I think we have a logic bug in resolve_doc
            #       Specifically, cur_doc.rev is always in the final vector
            #       clock of revisions that we supersede, even if it wasn't in
            #       conflicted_doc_revs. We still add it as a conflict, but the
            #       fact that _put_doc_if_newer propagates resolutions means I
            #       think that conflict could accidentally be resolved. We need
            #       to add a test for this case first. (create a rev, create a
            #       conflict, create another conflict, resolve the first rev
            #       and first conflict, then make sure that the resolved
            #       rev doesn't supersede the second conflict rev.) It *might*
            #       not matter, because the superseding rev is in as a
            #       conflict, but it does seem incorrect
            new_rev = self._ensure_maximal_rev(cur_doc.rev,
                                               conflicted_doc_revs)
            superseded_revs = set(conflicted_doc_revs)
            c = self._db_handle.cursor()
            doc.rev = new_rev
            if cur_doc.rev in superseded_revs:
                self._put_and_update_indexes(cur_doc, doc)
            else:
                self._add_conflict(c, doc.doc_id, new_rev, doc.get_json())
            # TODO: Is there some way that we could construct a rev that would
            #       end up in superseded_revs, such that we add a conflict, and
            #       then immediately delete it?
            self._delete_conflicts(c, doc, superseded_revs)

    def list_indexes(self):
        """Return the list of indexes and their definitions."""
        c = self._db_handle.cursor()
        # TODO: How do we test the ordering?
        c.execute("SELECT name, field FROM index_definitions"
                  " ORDER BY name, offset")
        definitions = []
        cur_name = None
        for name, field in c.fetchall():
            if cur_name != name:
                definitions.append((name, []))
                cur_name = name
            definitions[-1][-1].append(field)
        return definitions

    def _get_index_definition(self, index_name):
        """Return the stored definition for a given index_name."""
        c = self._db_handle.cursor()
        c.execute("SELECT field FROM index_definitions"
                  " WHERE name = ? ORDER BY offset", (index_name,))
        fields = [x[0] for x in c.fetchall()]
        if not fields:
            raise errors.IndexDoesNotExist
        return fields

    @staticmethod
    def _strip_glob(value):
        """Remove the trailing * from a value."""
        assert value[-1] == '*'
        return value[:-1]

    def _format_query(self, definition, key_values):
        # First, build the definition. We join the document_fields table
        # against itself, as many times as the 'width' of our definition.
        # We then do a query for each key_value, one-at-a-time.
        # Note: All of these strings are static, we could cache them, etc.
        tables = ["document_fields d%d" % i for i in range(len(definition))]
        novalue_where = ["d.doc_id = d%d.doc_id"
                         " AND d%d.field_name = ?"
                         % (i, i) for i in range(len(definition))]
        wildcard_where = [novalue_where[i]
                          + (" AND d%d.value NOT NULL" % (i,))
                          for i in range(len(definition))]
        exact_where = [novalue_where[i]
                       + (" AND d%d.value = ?" % (i,))
                       for i in range(len(definition))]
        like_where = [novalue_where[i]
                      + (" AND d%d.value GLOB ?" % (i,))
                      for i in range(len(definition))]
        is_wildcard = False
        # Merge the lists together, so that:
        # [field1, field2, field3], [val1, val2, val3]
        # Becomes:
        # (field1, val1, field2, val2, field3, val3)
        args = []
        where = []
        for idx, (field, value) in enumerate(zip(definition, key_values)):
            args.append(field)
            if value.endswith('*'):
                if value == '*':
                    where.append(wildcard_where[idx])
                else:
                    # This is a glob match
                    if is_wildcard:
                        # We can't have a partial wildcard following
                        # another wildcard
                        raise errors.InvalidGlobbing
                    where.append(like_where[idx])
                    args.append(value)
                is_wildcard = True
            else:
                if is_wildcard:
                    raise errors.InvalidGlobbing
                where.append(exact_where[idx])
                args.append(value)
        statement = (
            "SELECT d.doc_id, d.doc_rev, d.content, count(c.doc_rev) FROM "
            "document d, %s LEFT OUTER JOIN conflicts c ON c.doc_id = "
            "d.doc_id WHERE %s GROUP BY d.doc_id, d.doc_rev, d.content ORDER "
            "BY %s;" % (', '.join(tables), ' AND '.join(where), ', '.join(
                ['d%d.value' % i for i in range(len(definition))])))
        return statement, args

    def get_from_index(self, index_name, *key_values):
        definition = self._get_index_definition(index_name)
        if len(key_values) != len(definition):
            raise errors.InvalidValueForIndex()
        statement, args = self._format_query(definition, key_values)
        c = self._db_handle.cursor()
        try:
            c.execute(statement, tuple(args))
        except dbapi2.OperationalError, e:
            raise dbapi2.OperationalError(str(e) +
                '\nstatement: %s\nargs: %s\n' % (statement, args))
        res = c.fetchall()
        results = []
        for row in res:
            doc = self._factory(row[0], row[1], row[2])
            doc.has_conflicts = row[3] > 0
            results.append(doc)
        return results

    def _format_range_query(self, definition, start_value, end_value):
        tables = ["document_fields d%d" % i for i in range(len(definition))]
        novalue_where = [
            "d.doc_id = d%d.doc_id AND d%d.field_name = ?" % (i, i) for i in
            range(len(definition))]
        wildcard_where = [
            novalue_where[i] + (" AND d%d.value NOT NULL" % (i,)) for i in
            range(len(definition))]
        like_where = [
            novalue_where[i] + (
                " AND (d%d.value < ? OR d%d.value GLOB ?)" % (i, i)) for i in
            range(len(definition))]
        range_where_lower = [
            novalue_where[i] + (" AND d%d.value >= ?" % (i,)) for i in
            range(len(definition))]
        range_where_upper = [
            novalue_where[i] + (" AND d%d.value <= ?" % (i,)) for i in
            range(len(definition))]
        args = []
        where = []
        if start_value:
            if isinstance(start_value, basestring):
                start_value = (start_value,)
            if len(start_value) != len(definition):
                raise errors.InvalidValueForIndex()
            is_wildcard = False
            for idx, (field, value) in enumerate(zip(definition, start_value)):
                args.append(field)
                if value.endswith('*'):
                    if value == '*':
                        where.append(wildcard_where[idx])
                    else:
                        # This is a glob match
                        if is_wildcard:
                            # We can't have a partial wildcard following
                            # another wildcard
                            raise errors.InvalidGlobbing
                        where.append(range_where_lower[idx])
                        args.append(self._strip_glob(value))
                    is_wildcard = True
                else:
                    if is_wildcard:
                        raise errors.InvalidGlobbing
                    where.append(range_where_lower[idx])
                    args.append(value)
        if end_value:
            if isinstance(end_value, basestring):
                end_value = (end_value,)
            if len(end_value) != len(definition):
                raise errors.InvalidValueForIndex()
            is_wildcard = False
            for idx, (field, value) in enumerate(zip(definition, end_value)):
                args.append(field)
                if value.endswith('*'):
                    if value == '*':
                        where.append(wildcard_where[idx])
                    else:
                        # This is a glob match
                        if is_wildcard:
                            # We can't have a partial wildcard following
                            # another wildcard
                            raise errors.InvalidGlobbing
                        where.append(like_where[idx])
                        args.append(self._strip_glob(value))
                        args.append(value)
                    is_wildcard = True
                else:
                    if is_wildcard:
                        raise errors.InvalidGlobbing
                    where.append(range_where_upper[idx])
                    args.append(value)
        statement = (
            "SELECT d.doc_id, d.doc_rev, d.content, count(c.doc_rev) FROM "
            "document d, %s LEFT OUTER JOIN conflicts c ON c.doc_id = "
            "d.doc_id WHERE %s GROUP BY d.doc_id, d.doc_rev, d.content ORDER "
            "BY %s;" % (', '.join(tables), ' AND '.join(where), ', '.join(
                ['d%d.value' % i for i in range(len(definition))])))
        return statement, args

    def get_range_from_index(self, index_name, start_value=None,
                             end_value=None):
        """Return all documents with key values in the specified range."""
        definition = self._get_index_definition(index_name)
        statement, args = self._format_range_query(
            definition, start_value, end_value)
        c = self._db_handle.cursor()
        try:
            c.execute(statement, tuple(args))
        except dbapi2.OperationalError, e:
            raise dbapi2.OperationalError(str(e) +
                '\nstatement: %s\nargs: %s\n' % (statement, args))
        res = c.fetchall()
        results = []
        for row in res:
            doc = self._factory(row[0], row[1], row[2])
            doc.has_conflicts = row[3] > 0
            results.append(doc)
        return results

    def get_index_keys(self, index_name):
        c = self._db_handle.cursor()
        definition = self._get_index_definition(index_name)
        value_fields = ', '.join([
            'd%d.value' % i for i in range(len(definition))])
        tables = ["document_fields d%d" % i for i in range(len(definition))]
        novalue_where = [
            "d.doc_id = d%d.doc_id AND d%d.field_name = ?" % (i, i) for i in
            range(len(definition))]
        where = [
            novalue_where[i] + (" AND d%d.value NOT NULL" % (i,)) for i in
            range(len(definition))]
        statement = (
            "SELECT %s FROM document d, %s WHERE %s GROUP BY %s;" % (
                value_fields, ', '.join(tables), ' AND '.join(where),
                value_fields))
        try:
            c.execute(statement, tuple(definition))
        except dbapi2.OperationalError, e:
            raise dbapi2.OperationalError(str(e) +
                '\nstatement: %s\nargs: %s\n' % (statement, tuple(definition)))
        return c.fetchall()

    def delete_index(self, index_name):
        with self._db_handle:
            c = self._db_handle.cursor()
            c.execute("DELETE FROM index_definitions WHERE name = ?",
                      (index_name,))
            c.execute(
                "DELETE FROM document_fields WHERE document_fields.field_name "
                " NOT IN (SELECT field from index_definitions)")


class SQLCipherSyncTarget(CommonSyncTarget):

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


class SQLCipherPartialExpandDatabase(SQLCipherDatabase):
    """An SQLCipher Backend that expands documents into a document_field table.

    It stores the original document text in document.doc. For fields that are
    indexed, the data goes into document_fields.
    """

    _index_storage_value = 'expand referenced'

    def _get_indexed_fields(self):
        """Determine what fields are indexed."""
        c = self._db_handle.cursor()
        c.execute("SELECT field FROM index_definitions")
        return set([x[0] for x in c.fetchall()])

    def _evaluate_index(self, raw_doc, field):
        parser = query_parser.Parser()
        getter = parser.parse(field)
        return getter.get(raw_doc)

    def _put_and_update_indexes(self, old_doc, doc):
        c = self._db_handle.cursor()
        if doc and not doc.is_tombstone():
            raw_doc = json.loads(doc.get_json())
        else:
            raw_doc = {}
        if old_doc is not None:
            c.execute("UPDATE document SET doc_rev=?, content=?"
                      " WHERE doc_id = ?",
                      (doc.rev, doc.get_json(), doc.doc_id))
            c.execute("DELETE FROM document_fields WHERE doc_id = ?",
                      (doc.doc_id,))
        else:
            c.execute("INSERT INTO document (doc_id, doc_rev, content)"
                      " VALUES (?, ?, ?)",
                      (doc.doc_id, doc.rev, doc.get_json()))
        indexed_fields = self._get_indexed_fields()
        if indexed_fields:
            # It is expected that len(indexed_fields) is shorter than
            # len(raw_doc)
            getters = [(field, self._parse_index_definition(field))
                       for field in indexed_fields]
            self._update_indexes(doc.doc_id, raw_doc, getters, c)
        trans_id = self._allocate_transaction_id()
        c.execute("INSERT INTO transaction_log(doc_id, transaction_id)"
                  " VALUES (?, ?)", (doc.doc_id, trans_id))

    def create_index(self, index_name, *index_expressions):
        with self._db_handle:
            c = self._db_handle.cursor()
            cur_fields = self._get_indexed_fields()
            definition = [(index_name, idx, field)
                          for idx, field in enumerate(index_expressions)]
            try:
                c.executemany("INSERT INTO index_definitions VALUES (?, ?, ?)",
                              definition)
            except dbapi2.IntegrityError as e:
                stored_def = self._get_index_definition(index_name)
                if stored_def == [x[-1] for x in definition]:
                    return
                raise errors.IndexNameTakenError, e, sys.exc_info()[2]
            new_fields = set(
                [f for f in index_expressions if f not in cur_fields])
            if new_fields:
                self._update_all_indexes(new_fields)

    def _iter_all_docs(self):
        c = self._db_handle.cursor()
        c.execute("SELECT doc_id, content FROM document")
        while True:
            next_rows = c.fetchmany()
            if not next_rows:
                break
            for row in next_rows:
                yield row

    def _update_all_indexes(self, new_fields):
        """Iterate all the documents, and add content to document_fields.

        :param new_fields: The index definitions that need to be added.
        """
        getters = [(field, self._parse_index_definition(field))
                   for field in new_fields]
        c = self._db_handle.cursor()
        for doc_id, doc in self._iter_all_docs():
            if doc is None:
                continue
            raw_doc = json.loads(doc)
            self._update_indexes(doc_id, raw_doc, getters, c)

SQLCipherDatabase.register_implementation(SQLCipherPartialExpandDatabase)
