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

"""U1DB"""

try:
    import simplejson as json
except ImportError:
    import json  # noqa

from u1db.errors import InvalidJSON, InvalidContent

__version_info__ = (0, 1, 4)
__version__ = '.'.join(map(str, __version_info__))


def open(path, create, document_factory=None):
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
    return sqlite_backend.SQLiteDatabase.open_database(
        path, create=create, document_factory=document_factory)


# constraints on database names (relevant for remote access, as regex)
DBNAME_CONSTRAINTS = r"[a-zA-Z0-9][a-zA-Z0-9.-]*"

# constraints on doc ids (as regex)
# (no slashes, and no characters outside the ascii range)
DOC_ID_CONSTRAINTS = r"[a-zA-Z0-9.%_-]+"


class Database(object):
    """A JSON Document data store.

    This data store can be synchronized with other u1db.Database instances.
    """

    def set_document_factory(self, factory):
        """Set the document factory that will be used to create objects to be
        returned as documents by the database.

        :param factory: A function that returns an object which at minimum must
            satisfy the same interface as does the class DocumentBase.
            Subclassing that class is the easiest way to create such
            a function.
        """
        raise NotImplementedError(self.set_document_factory)

    def set_document_size_limit(self, limit):
        """Set the maximum allowed document size for this database.

        :param limit: Maximum allowed document size in bytes.
        """
        raise NotImplementedError(self.set_document_size_limit)

    def whats_changed(self, old_generation=0):
        """Return a list of documents that have changed since old_generation.
        This allows APPS to only store a db generation before going
        'offline', and then when coming back online they can use this
        data to update whatever extra data they are storing.

        :param old_generation: The generation of the database in the old
            state.
        :return: (generation, trans_id, [(doc_id, generation, trans_id),...])
            The current generation of the database, its associated transaction
            id, and a list of of changed documents since old_generation,
            represented by tuples with for each document its doc_id and the
            generation and transaction id corresponding to the last intervening
            change and sorted by generation (old changes first)
        """
        raise NotImplementedError(self.whats_changed)

    def get_doc(self, doc_id, include_deleted=False):
        """Get the JSON string for the given document.

        :param doc_id: The unique document identifier
        :param include_deleted: If set to True, deleted documents will be
            returned with empty content. Otherwise asking for a deleted
            document will return None.
        :return: a Document object.
        """
        raise NotImplementedError(self.get_doc)

    def get_docs(self, doc_ids, check_for_conflicts=True,
                 include_deleted=False):
        """Get the JSON content for many documents.

        :param doc_ids: A list of document identifiers.
        :param check_for_conflicts: If set to False, then the conflict check
            will be skipped, and 'None' will be returned instead of True/False.
        :param include_deleted: If set to True, deleted documents will be
            returned with empty content. Otherwise deleted documents will not
            be included in the results.
        :return: iterable giving the Document object for each document id
            in matching doc_ids order.
        """
        raise NotImplementedError(self.get_docs)

    def get_all_docs(self, include_deleted=False):
        """Get the JSON content for all documents in the database.

        :param include_deleted: If set to True, deleted documents will be
            returned with empty content. Otherwise deleted documents will not
            be included in the results.
        :return: (generation, [Document])
            The current generation of the database, followed by a list of all
            the documents in the database.
        """
        raise NotImplementedError(self.get_all_docs)

    def create_doc(self, content, doc_id=None):
        """Create a new document.

        You can optionally specify the document identifier, but the document
        must not already exist. See 'put_doc' if you want to override an
        existing document.
        If the database specifies a maximum document size and the document
        exceeds it, create will fail and raise a DocumentTooBig exception.

        :param content: A Python dictionary.
        :param doc_id: An optional identifier specifying the document id.
        :return: Document
        """
        raise NotImplementedError(self.create_doc)

    def create_doc_from_json(self, json, doc_id=None):
        """Create a new document.

        You can optionally specify the document identifier, but the document
        must not already exist. See 'put_doc' if you want to override an
        existing document.
        If the database specifies a maximum document size and the document
        exceeds it, create will fail and raise a DocumentTooBig exception.

        :param json: The JSON document string
        :param doc_id: An optional identifier specifying the document id.
        :return: Document
        """
        raise NotImplementedError(self.create_doc_from_json)

    def put_doc(self, doc):
        """Update a document.
        If the document currently has conflicts, put will fail.
        If the database specifies a maximum document size and the document
        exceeds it, put will fail and raise a DocumentTooBig exception.

        :param doc: A Document with new content.
        :return: new_doc_rev - The new revision identifier for the document.
            The Document object will also be updated.
        """
        raise NotImplementedError(self.put_doc)

    def delete_doc(self, doc):
        """Mark a document as deleted.
        Will abort if the current revision doesn't match doc.rev.
        This will also set doc.content to None.
        """
        raise NotImplementedError(self.delete_doc)

    def create_index(self, index_name, *index_expressions):
        """Create an named index, which can then be queried for future lookups.
        Creating an index which already exists is not an error, and is cheap.
        Creating an index which does not match the index_expressions of the
        existing index is an error.
        Creating an index will block until the expressions have been evaluated
        and the index generated.

        :param index_name: A unique name which can be used as a key prefix
        :param index_expressions: index expressions defining the index
            information.

            Examples:

            "fieldname", or "fieldname.subfieldname" to index alphabetically
            sorted on the contents of a field.

            "number(fieldname, width)", "lower(fieldname)"
        """
        raise NotImplementedError(self.create_index)

    def delete_index(self, index_name):
        """Remove a named index.

        :param index_name: The name of the index we are removing
        """
        raise NotImplementedError(self.delete_index)

    def list_indexes(self):
        """List the definitions of all known indexes.

        :return: A list of [('index-name', ['field', 'field2'])] definitions.
        """
        raise NotImplementedError(self.list_indexes)

    def get_from_index(self, index_name, *key_values):
        """Return documents that match the keys supplied.

        You must supply exactly the same number of values as have been defined
        in the index. It is possible to do a prefix match by using '*' to
        indicate a wildcard match. You can only supply '*' to trailing entries,
        (eg 'val', '*', '*' is allowed, but '*', 'val', 'val' is not.)
        It is also possible to append a '*' to the last supplied value (eg
        'val*', '*', '*' or 'val', 'val*', '*', but not 'val*', 'val', '*')

        :param index_name: The index to query
        :param key_values: values to match. eg, if you have
            an index with 3 fields then you would have:
            get_from_index(index_name, val1, val2, val3)
        :return: List of [Document]
        """
        raise NotImplementedError(self.get_from_index)

    def get_range_from_index(self, index_name, start_value, end_value):
        """Return documents that fall within the specified range.

        Both ends of the range are inclusive. For both start_value and
        end_value, one must supply exactly the same number of values as have
        been defined in the index, or pass None. In case of a single column
        index, a string is accepted as an alternative for a tuple with a single
        value. It is possible to do a prefix match by using '*' to indicate
        a wildcard match. You can only supply '*' to trailing entries, (eg
        'val', '*', '*' is allowed, but '*', 'val', 'val' is not.) It is also
        possible to append a '*' to the last supplied value (eg 'val*', '*',
        '*' or 'val', 'val*', '*', but not 'val*', 'val', '*')

        :param index_name: The index to query
        :param start_values: tuples of values that define the lower bound of
            the range. eg, if you have an index with 3 fields then you would
            have: (val1, val2, val3)
        :param end_values: tuples of values that define the upper bound of the
            range. eg, if you have an index with 3 fields then you would have:
            (val1, val2, val3)
        :return: List of [Document]
        """
        raise NotImplementedError(self.get_range_from_index)

    def get_index_keys(self, index_name):
        """Return all keys under which documents are indexed in this index.

        :param index_name: The index to query
        :return: [] A list of tuples of indexed keys.
        """
        raise NotImplementedError(self.get_index_keys)

    def get_doc_conflicts(self, doc_id):
        """Get the list of conflicts for the given document.

        The order of the conflicts is such that the first entry is the value
        that would be returned by "get_doc".

        :return: [doc] A list of the Document entries that are conflicted.
        """
        raise NotImplementedError(self.get_doc_conflicts)

    def resolve_doc(self, doc, conflicted_doc_revs):
        """Mark a document as no longer conflicted.

        We take the list of revisions that the client knows about that it is
        superseding. This may be a different list from the actual current
        conflicts, in which case only those are removed as conflicted.  This
        may fail if the conflict list is significantly different from the
        supplied information. (sync could have happened in the background from
        the time you GET_DOC_CONFLICTS until the point where you RESOLVE)

        :param doc: A Document with the new content to be inserted.
        :param conflicted_doc_revs: A list of revisions that the new content
            supersedes.
        """
        raise NotImplementedError(self.resolve_doc)

    def get_sync_target(self):
        """Return a SyncTarget object, for another u1db to synchronize with.

        :return: An instance of SyncTarget.
        """
        raise NotImplementedError(self.get_sync_target)

    def close(self):
        """Release any resources associated with this database."""
        raise NotImplementedError(self.close)

    def sync(self, url, creds=None, autocreate=True):
        """Synchronize documents with remote replica exposed at url.

        :param url: the url of the target replica to sync with.
        :param creds: optional dictionary giving credentials
            to authorize the operation with the server. For using OAuth
            the form of creds is:
                {'oauth': {
                 'consumer_key': ...,
                 'consumer_secret': ...,
                 'token_key': ...,
                 'token_secret': ...
                }}
        :param autocreate: ask the target to create the db if non-existent.
        :return: local_gen_before_sync The local generation before the
            synchronisation was performed. This is useful to pass into
            whatschanged, if an application wants to know which documents were
            affected by a synchronisation.
        """
        from u1db.sync import Synchronizer
        from u1db.remote.http_target import HTTPSyncTarget
        return Synchronizer(self, HTTPSyncTarget(url, creds=creds)).sync(
            autocreate=autocreate)

    def _get_replica_gen_and_trans_id(self, other_replica_uid):
        """Return the last known generation and transaction id for the other db
        replica.

        When you do a synchronization with another replica, the Database keeps
        track of what generation the other database replica was at, and what
        the associated transaction id was.  This is used to determine what data
        needs to be sent, and if two databases are claiming to be the same
        replica.

        :param other_replica_uid: The identifier for the other replica.
        :return: (gen, trans_id) The generation and transaction id we
            encountered during synchronization. If we've never synchronized
            with the replica, this is (0, '').
        """
        raise NotImplementedError(self._get_replica_gen_and_trans_id)

    def _set_replica_gen_and_trans_id(self, other_replica_uid,
                                      other_generation, other_transaction_id):
        """Set the last-known generation and transaction id for the other
        database replica.

        We have just performed some synchronization, and we want to track what
        generation the other replica was at. See also
        _get_replica_gen_and_trans_id.
        :param other_replica_uid: The U1DB identifier for the other replica.
        :param other_generation: The generation number for the other replica.
        :param other_transaction_id: The transaction id associated with the
            generation.
        """
        raise NotImplementedError(self._set_replica_gen_and_trans_id)

    def _put_doc_if_newer(self, doc, save_conflict, replica_uid, replica_gen,
                          replica_trans_id=''):
        """Insert/update document into the database with a given revision.

        This api is used during synchronization operations.

        If a document would conflict and save_conflict is set to True, the
        content will be selected as the 'current' content for doc.doc_id,
        even though doc.rev doesn't supersede the currently stored revision.
        The currently stored document will be added to the list of conflict
        alternatives for the given doc_id.

        This forces the new content to be 'current' so that we get convergence
        after synchronizing, even if people don't resolve conflicts. Users can
        then notice that their content is out of date, update it, and
        synchronize again. (The alternative is that users could synchronize and
        think the data has propagated, but their local copy looks fine, and the
        remote copy is never updated again.)

        :param doc: A Document object
        :param save_conflict: If this document is a conflict, do you want to
            save it as a conflict, or just ignore it.
        :param replica_uid: A unique replica identifier.
        :param replica_gen: The generation of the replica corresponding to the
            this document. The replica arguments are optional, but are used
            during synchronization.
        :param replica_trans_id: The transaction_id associated with the
            generation.
        :return: (state, at_gen) -  If we don't have doc_id already,
            or if doc_rev supersedes the existing document revision,
            then the content will be inserted, and state is 'inserted'.
            If doc_rev is less than or equal to the existing revision,
            then the put is ignored and state is respecitvely 'superseded'
            or 'converged'.
            If doc_rev is not strictly superseded or supersedes, then
            state is 'conflicted'. The document will not be inserted if
            save_conflict is False.
            For 'inserted' or 'converged', at_gen is the insertion/current
            generation.
        """
        raise NotImplementedError(self._put_doc_if_newer)


class DocumentBase(object):
    """Container for handling a single document.

    :ivar doc_id: Unique identifier for this document.
    :ivar rev: The revision identifier of the document.
    :ivar json_string: The JSON string for this document.
    :ivar has_conflicts: Boolean indicating if this document has conflicts
    """

    def __init__(self, doc_id, rev, json_string, has_conflicts=False):
        self.doc_id = doc_id
        self.rev = rev
        if json_string is not None:
            try:
                value = json.loads(json_string)
            except json.JSONDecodeError:
                raise InvalidJSON
            if not isinstance(value, dict):
                raise InvalidJSON
        self._json = json_string
        self.has_conflicts = has_conflicts

    def same_content_as(self, other):
        """Compare the content of two documents."""
        if self._json:
            c1 = json.loads(self._json)
        else:
            c1 = None
        if other._json:
            c2 = json.loads(other._json)
        else:
            c2 = None
        return c1 == c2

    def __repr__(self):
        if self.has_conflicts:
            extra = ', conflicted'
        else:
            extra = ''
        return '%s(%s, %s%s, %r)' % (self.__class__.__name__, self.doc_id,
                                     self.rev, extra, self.get_json())

    def __hash__(self):
        raise NotImplementedError(self.__hash__)

    def __eq__(self, other):
        if not isinstance(other, Document):
            return NotImplemented
        return (
            self.doc_id == other.doc_id and self.rev == other.rev and
            self.same_content_as(other) and self.has_conflicts ==
            other.has_conflicts)

    def __lt__(self, other):
        """This is meant for testing, not part of the official api.

        It is implemented so that sorted([Document, Document]) can be used.
        It doesn't imply that users would want their documents to be sorted in
        this order.
        """
        # Since this is just for testing, we don't worry about comparing
        # against things that aren't a Document.
        return ((self.doc_id, self.rev, self.get_json())
            < (other.doc_id, other.rev, other.get_json()))

    def get_json(self):
        """Get the json serialization of this document."""
        if self._json is not None:
            return self._json
        return None

    def get_size(self):
        """Calculate the total size of the document."""
        size = 0
        json = self.get_json()
        if json:
            size += len(json)
        if self.rev:
            size += len(self.rev)
        if self.doc_id:
            size += len(self.doc_id)
        return size

    def set_json(self, json_string):
        """Set the json serialization of this document."""
        if json_string is not None:
            try:
                value = json.loads(json_string)
            except json.JSONDecodeError:
                raise InvalidJSON
            if not isinstance(value, dict):
                raise InvalidJSON
        self._json = json_string

    def make_tombstone(self):
        """Make this document into a tombstone."""
        self._json = None

    def is_tombstone(self):
        """Return True if the document is a tombstone, False otherwise."""
        if self._json is not None:
            return False
        return True


class Document(DocumentBase):
    """Container for handling a single document.

    :ivar doc_id: Unique identifier for this document.
    :ivar rev: The revision identifier of the document.
    :ivar json: The JSON string for this document.
    :ivar has_conflicts: Boolean indicating if this document has conflicts
    """

    # The following part of the API is optional: no implementation is forced to
    # have it but if the language supports dictionaries/hashtables, it makes
    # Documents a lot more user friendly.

    def __init__(self, doc_id=None, rev=None, json='{}', has_conflicts=False):
        # TODO: We convert the json in the superclass to check its validity so
        # we might as well set _content here directly since the price is
        # already being paid.
        super(Document, self).__init__(doc_id, rev, json, has_conflicts)
        self._content = None

    def same_content_as(self, other):
        """Compare the content of two documents."""
        if self._json:
            c1 = json.loads(self._json)
        else:
            c1 = self._content
        if other._json:
            c2 = json.loads(other._json)
        else:
            c2 = other._content
        return c1 == c2

    def get_json(self):
        """Get the json serialization of this document."""
        json_string = super(Document, self).get_json()
        if json_string is not None:
            return json_string
        if self._content is not None:
            return json.dumps(self._content)
        return None

    def set_json(self, json):
        """Set the json serialization of this document."""
        self._content = None
        super(Document, self).set_json(json)

    def make_tombstone(self):
        """Make this document into a tombstone."""
        self._content = None
        super(Document, self).make_tombstone()

    def is_tombstone(self):
        """Return True if the document is a tombstone, False otherwise."""
        if self._content is not None:
            return False
        return super(Document, self).is_tombstone()

    def _get_content(self):
        """Get the dictionary representing this document."""
        if self._json is not None:
            self._content = json.loads(self._json)
            self._json = None
        if self._content is not None:
            return self._content
        return None

    def _set_content(self, content):
        """Set the dictionary representing this document."""
        try:
            tmp = json.dumps(content)
        except TypeError:
            raise InvalidContent(
                "Can not be converted to JSON: %r" % (content,))
        if not tmp.startswith('{'):
            raise InvalidContent(
                "Can not be converted to a JSON object: %r." % (content,))
        # We might as well store the JSON at this point since we did the work
        # of encoding it, and it doesn't lose any information.
        self._json = tmp
        self._content = None

    content = property(
        _get_content, _set_content, doc="Content of the Document.")

    # End of optional part.


class SyncTarget(object):
    """Functionality for using a Database as a synchronization target."""

    def get_sync_info(self, source_replica_uid):
        """Return information about known state.

        Return the replica_uid and the current database generation of this
        database, and the last-seen database generation for source_replica_uid

        :param source_replica_uid: Another replica which we might have
            synchronized with in the past.
        :return: (target_replica_uid, target_replica_generation,
            target_trans_id, source_replica_last_known_generation,
            source_replica_last_known_transaction_id)
        """
        raise NotImplementedError(self.get_sync_info)

    def record_sync_info(self, source_replica_uid, source_replica_generation,
                         source_replica_transaction_id):
        """Record tip information for another replica.

        After sync_exchange has been processed, the caller will have
        received new content from this replica. This call allows the
        source replica instigating the sync to inform us what their
        generation became after applying the documents we returned.

        This is used to allow future sync operations to not need to repeat data
        that we just talked about. It also means that if this is called at the
        wrong time, there can be database records that will never be
        synchronized.

        :param source_replica_uid: The identifier for the source replica.
        :param source_replica_generation:
            The database generation for the source replica.
        :param source_replica_transaction_id: The transaction id associated
            with the source replica generation.
        """
        raise NotImplementedError(self.record_sync_info)

    def sync_exchange(self, docs_by_generation, source_replica_uid,
                      last_known_generation, last_known_trans_id,
                      return_doc_cb, ensure_callback=None):
        """Incorporate the documents sent from the source replica.

        This is not meant to be called by client code directly, but is used as
        part of sync().

        This adds docs to the local store, and determines documents that need
        to be returned to the source replica.

        Documents must be supplied in docs_by_generation paired with
        the generation of their latest change in order from the oldest
        change to the newest, that means from the oldest generation to
        the newest.

        Documents are also returned paired with the generation of
        their latest change in order from the oldest change to the
        newest.

        :param docs_by_generation: A list of [(Document, generation,
            transaction_id)] tuples indicating documents which should be
            updated on this replica paired with the generation and transaction
            id of their latest change.
        :param source_replica_uid: The source replica's identifier
        :param last_known_generation: The last generation that the source
            replica knows about this target replica
        :param last_known_trans_id: The last transaction id that the source
            replica knows about this target replica
        :param: return_doc_cb(doc, gen): is a callback
            used to return documents to the source replica, it will
            be invoked in turn with Documents that have changed since
            last_known_generation together with the generation of
            their last change.
        :param: ensure_callback(replica_uid): if set the target may create
            the target db if not yet existent, the callback can then
            be used to inform of the created db replica uid.
        :return: new_generation - After applying docs_by_generation, this is
            the current generation for this replica
        """
        raise NotImplementedError(self.sync_exchange)

    def _set_trace_hook(self, cb):
        """Set a callback that will be invoked to trace database actions.

        The callback will be passed a string indicating the current state, and
        the sync target object.  Implementations do not have to implement this
        api, it is used by the test suite.

        :param cb: A callable that takes cb(state)
        """
        raise NotImplementedError(self._set_trace_hook)

    def _set_trace_hook_shallow(self, cb):
        """Set a callback that will be invoked to trace database actions.

        Similar to _set_trace_hook, for implementations that don't offer
        state changes from the inner working of sync_exchange().

        :param cb: A callable that takes cb(state)
        """
        self._set_trace_hook(cb)
