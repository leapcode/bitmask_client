# Copyright 2011-2012 Canonical Ltd.
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
#
"""A Cython wrapper around the C implementation of U1DB Database backend."""

cdef extern from "Python.h":
    object PyString_FromStringAndSize(char *s, Py_ssize_t n)
    int PyString_AsStringAndSize(object o, char **buf, Py_ssize_t *length
                                 ) except -1
    char *PyString_AsString(object) except NULL
    char *PyString_AS_STRING(object)
    char *strdup(char *)
    void *calloc(size_t, size_t)
    void free(void *)
    ctypedef struct FILE:
        pass
    fprintf(FILE *, char *, ...)
    FILE *stderr
    size_t strlen(char *)

cdef extern from "stdarg.h":
    ctypedef struct va_list:
        pass
    void va_start(va_list, void*)
    void va_start_int "va_start" (va_list, int)
    void va_end(va_list)

cdef extern from "u1db/u1db.h":
    ctypedef struct u1database:
        pass
    ctypedef struct u1db_document:
        char *doc_id
        size_t doc_id_len
        char *doc_rev
        size_t doc_rev_len
        char *json
        size_t json_len
        int has_conflicts
    # Note: u1query is actually defined in u1db_internal.h, and in u1db.h it is
    #       just an opaque pointer. However, older versions of Cython don't let
    #       you have a forward declaration and a full declaration, so we just
    #       expose the whole thing here.
    ctypedef struct u1query:
        char *index_name
        int num_fields
        char **fields
    cdef struct u1db_oauth_creds:
        int auth_kind
        char *consumer_key
        char *consumer_secret
        char *token_key
        char *token_secret
    ctypedef union u1db_creds
    ctypedef u1db_creds* const_u1db_creds_ptr "const u1db_creds *"

    ctypedef char* const_char_ptr "const char*"
    ctypedef int (*u1db_doc_callback)(void *context, u1db_document *doc)
    ctypedef int (*u1db_key_callback)(void *context, int num_fields,
                                      const_char_ptr *key)
    ctypedef int (*u1db_doc_gen_callback)(void *context,
        u1db_document *doc, int gen, const_char_ptr trans_id)
    ctypedef int (*u1db_trans_info_callback)(void *context,
        const_char_ptr doc_id, int gen, const_char_ptr trans_id)

    u1database * u1db_open(char *fname)
    void u1db_free(u1database **)
    int u1db_set_replica_uid(u1database *, char *replica_uid)
    int u1db_set_document_size_limit(u1database *, int limit)
    int u1db_get_replica_uid(u1database *, const_char_ptr *replica_uid)
    int u1db_create_doc_from_json(u1database *db, char *json, char *doc_id,
                                  u1db_document **doc)
    int u1db_delete_doc(u1database *db, u1db_document *doc)
    int u1db_get_doc(u1database *db, char *doc_id, int include_deleted,
                     u1db_document **doc)
    int u1db_get_docs(u1database *db, int n_doc_ids, const_char_ptr *doc_ids,
                      int check_for_conflicts, int include_deleted,
                      void *context, u1db_doc_callback cb)
    int u1db_get_all_docs(u1database *db, int include_deleted, int *generation,
                          void *context, u1db_doc_callback cb)
    int u1db_put_doc(u1database *db, u1db_document *doc)
    int u1db__validate_source(u1database *db, const_char_ptr replica_uid,
                              int replica_gen, const_char_ptr replica_trans_id)
    int u1db__put_doc_if_newer(u1database *db, u1db_document *doc,
                               int save_conflict, char *replica_uid,
                               int replica_gen, char *replica_trans_id,
                               int *state, int *at_gen)
    int u1db_resolve_doc(u1database *db, u1db_document *doc,
                         int n_revs, const_char_ptr *revs)
    int u1db_delete_doc(u1database *db, u1db_document *doc)
    int u1db_whats_changed(u1database *db, int *gen, char **trans_id,
                           void *context, u1db_trans_info_callback cb)
    int u1db__get_transaction_log(u1database *db, void *context,
                                  u1db_trans_info_callback cb)
    int u1db_get_doc_conflicts(u1database *db, char *doc_id, void *context,
                               u1db_doc_callback cb)
    int u1db_sync(u1database *db, const_char_ptr url,
                  const_u1db_creds_ptr creds, int *local_gen) nogil
    int u1db_create_index_list(u1database *db, char *index_name,
                               int n_expressions, const_char_ptr *expressions)
    int u1db_create_index(u1database *db, char *index_name, int n_expressions,
                          ...)
    int u1db_get_from_index_list(u1database *db, u1query *query, void *context,
                                 u1db_doc_callback cb, int n_values,
                                 const_char_ptr *values)
    int u1db_get_from_index(u1database *db, u1query *query, void *context,
                             u1db_doc_callback cb, int n_values, char *val0,
                             ...)
    int u1db_get_range_from_index(u1database *db, u1query *query,
                                  void *context, u1db_doc_callback cb,
                                  int n_values, const_char_ptr *start_values,
                                  const_char_ptr *end_values)
    int u1db_delete_index(u1database *db, char *index_name)
    int u1db_list_indexes(u1database *db, void *context,
                  int (*cb)(void *context, const_char_ptr index_name,
                            int n_expressions, const_char_ptr *expressions))
    int u1db_get_index_keys(u1database *db, char *index_name, void *context,
                            u1db_key_callback cb)
    int u1db_simple_lookup1(u1database *db, char *index_name, char *val1,
                            void *context, u1db_doc_callback cb)
    int u1db_query_init(u1database *db, char *index_name, u1query **query)
    void u1db_free_query(u1query **query)

    int U1DB_OK
    int U1DB_INVALID_PARAMETER
    int U1DB_REVISION_CONFLICT
    int U1DB_INVALID_DOC_ID
    int U1DB_DOCUMENT_ALREADY_DELETED
    int U1DB_DOCUMENT_DOES_NOT_EXIST
    int U1DB_NOT_IMPLEMENTED
    int U1DB_INVALID_JSON
    int U1DB_DOCUMENT_TOO_BIG
    int U1DB_USER_QUOTA_EXCEEDED
    int U1DB_INVALID_VALUE_FOR_INDEX
    int U1DB_INVALID_FIELD_SPECIFIER
    int U1DB_INVALID_GLOBBING
    int U1DB_BROKEN_SYNC_STREAM
    int U1DB_DUPLICATE_INDEX_NAME
    int U1DB_INDEX_DOES_NOT_EXIST
    int U1DB_INVALID_GENERATION
    int U1DB_INVALID_TRANSACTION_ID
    int U1DB_INVALID_TRANSFORMATION_FUNCTION
    int U1DB_UNKNOWN_OPERATION
    int U1DB_INTERNAL_ERROR
    int U1DB_TARGET_UNAVAILABLE

    int U1DB_INSERTED
    int U1DB_SUPERSEDED
    int U1DB_CONVERGED
    int U1DB_CONFLICTED

    int U1DB_OAUTH_AUTH

    void u1db_free_doc(u1db_document **doc)
    int u1db_doc_set_json(u1db_document *doc, char *json)
    int u1db_doc_get_size(u1db_document *doc)


cdef extern from "u1db/u1db_internal.h":
    ctypedef struct u1db_row:
        u1db_row *next
        int num_columns
        int *column_sizes
        unsigned char **columns

    ctypedef struct u1db_table:
        int status
        u1db_row *first_row

    ctypedef struct u1db_record:
        u1db_record *next
        char *doc_id
        char *doc_rev
        char *doc

    ctypedef struct u1db_sync_exchange:
        int target_gen
        int num_doc_ids
        char **doc_ids_to_return
        int *gen_for_doc_ids
        const_char_ptr *trans_ids_for_doc_ids

    ctypedef int (*u1db__trace_callback)(void *context, const_char_ptr state)
    ctypedef struct u1db_sync_target:
        int (*get_sync_info)(u1db_sync_target *st, char *source_replica_uid,
                             const_char_ptr *st_replica_uid, int *st_gen,
                             char **st_trans_id, int *source_gen,
                             char **source_trans_id) nogil
        int (*record_sync_info)(u1db_sync_target *st,
            char *source_replica_uid, int source_gen, char *trans_id) nogil
        int (*sync_exchange)(u1db_sync_target *st,
                             char *source_replica_uid, int n_docs,
                             u1db_document **docs, int *generations,
                             const_char_ptr *trans_ids,
                             int *target_gen, char **target_trans_id,
                             void *context, u1db_doc_gen_callback cb,
                             void *ensure_callback) nogil
        int (*sync_exchange_doc_ids)(u1db_sync_target *st,
                                     u1database *source_db, int n_doc_ids,
                                     const_char_ptr *doc_ids, int *generations,
                                     const_char_ptr *trans_ids,
                                     int *target_gen, char **target_trans_id,
                                     void *context,
                                     u1db_doc_gen_callback cb,
                                     void *ensure_callback) nogil
        int (*get_sync_exchange)(u1db_sync_target *st,
                                 char *source_replica_uid,
                                 int last_known_source_gen,
                                 u1db_sync_exchange **exchange) nogil
        void (*finalize_sync_exchange)(u1db_sync_target *st,
                                       u1db_sync_exchange **exchange) nogil
        int (*_set_trace_hook)(u1db_sync_target *st,
                               void *context, u1db__trace_callback cb) nogil


    void u1db__set_zero_delays()
    int u1db__get_generation(u1database *, int *db_rev)
    int u1db__get_document_size_limit(u1database *, int *limit)
    int u1db__get_generation_info(u1database *, int *db_rev, char **trans_id)
    int u1db__get_trans_id_for_gen(u1database *, int db_rev, char **trans_id)
    int u1db_validate_gen_and_trans_id(u1database *, int db_rev,
                                       const_char_ptr trans_id)
    char *u1db__allocate_doc_id(u1database *)
    int u1db__sql_close(u1database *)
    u1database *u1db__copy(u1database *)
    int u1db__sql_is_open(u1database *)
    u1db_table *u1db__sql_run(u1database *, char *sql, size_t n)
    void u1db__free_table(u1db_table **table)
    u1db_record *u1db__create_record(char *doc_id, char *doc_rev, char *doc)
    void u1db__free_records(u1db_record **)

    int u1db__allocate_document(char *doc_id, char *revision, char *content,
                                int has_conflicts, u1db_document **result)
    int u1db__generate_hex_uuid(char *)

    int u1db__get_replica_gen_and_trans_id(u1database *db, char *replica_uid,
                                           int *generation, char **trans_id)
    int u1db__set_replica_gen_and_trans_id(u1database *db, char *replica_uid,
                                           int generation, char *trans_id)
    int u1db__sync_get_machine_info(u1database *db, char *other_replica_uid,
                                    int *other_db_rev, char **my_replica_uid,
                                    int *my_db_rev)
    int u1db__sync_record_machine_info(u1database *db, char *replica_uid,
                                       int db_rev)
    int u1db__sync_exchange_seen_ids(u1db_sync_exchange *se, int *n_ids,
                                     const_char_ptr **doc_ids)
    int u1db__format_query(int n_fields, const_char_ptr *values, char **buf,
                           int *wildcard)
    int u1db__get_sync_target(u1database *db, u1db_sync_target **sync_target)
    int u1db__free_sync_target(u1db_sync_target **sync_target)
    int u1db__sync_db_to_target(u1database *db, u1db_sync_target *target,
                                int *local_gen_before_sync) nogil

    int u1db__sync_exchange_insert_doc_from_source(u1db_sync_exchange *se,
            u1db_document *doc, int source_gen, const_char_ptr trans_id)
    int u1db__sync_exchange_find_doc_ids_to_return(u1db_sync_exchange *se)
    int u1db__sync_exchange_return_docs(u1db_sync_exchange *se, void *context,
                                        int (*cb)(void *context,
                                                  u1db_document *doc, int gen,
                                                  const_char_ptr trans_id))
    int u1db__create_http_sync_target(char *url, u1db_sync_target **target)
    int u1db__create_oauth_http_sync_target(char *url,
        char *consumer_key, char *consumer_secret,
        char *token_key, char *token_secret,
        u1db_sync_target **target)

cdef extern from "u1db/u1db_http_internal.h":
    int u1db__format_sync_url(u1db_sync_target *st,
            const_char_ptr source_replica_uid, char **sync_url)
    int u1db__get_oauth_authorization(u1db_sync_target *st,
        char *http_method, char *url,
        char **oauth_authorization)


cdef extern from "u1db/u1db_vectorclock.h":
    ctypedef struct u1db_vectorclock_item:
        char *replica_uid
        int generation

    ctypedef struct u1db_vectorclock:
        int num_items
        u1db_vectorclock_item *items

    u1db_vectorclock *u1db__vectorclock_from_str(char *s)
    void u1db__free_vectorclock(u1db_vectorclock **clock)
    int u1db__vectorclock_increment(u1db_vectorclock *clock, char *replica_uid)
    int u1db__vectorclock_maximize(u1db_vectorclock *clock,
                                   u1db_vectorclock *other)
    int u1db__vectorclock_as_str(u1db_vectorclock *clock, char **result)
    int u1db__vectorclock_is_newer(u1db_vectorclock *maybe_newer,
                                   u1db_vectorclock *older)

from u1db import errors
from sqlite3 import dbapi2


cdef int _append_trans_info_to_list(void *context, const_char_ptr doc_id,
                                    int generation,
                                    const_char_ptr trans_id) with gil:
    a_list = <object>(context)
    doc = doc_id
    a_list.append((doc, generation, trans_id))
    return 0


cdef int _append_doc_to_list(void *context, u1db_document *doc) with gil:
    a_list = <object>context
    pydoc = CDocument()
    pydoc._doc = doc
    a_list.append(pydoc)
    return 0

cdef int _append_key_to_list(void *context, int num_fields,
                             const_char_ptr *key) with gil:
    a_list = <object>(context)
    field_list = []
    for i from 0 <= i < num_fields:
        field = key[i]
        field_list.append(field.decode('utf-8'))
    a_list.append(tuple(field_list))
    return 0

cdef _list_to_array(lst, const_char_ptr **res, int *count):
    cdef const_char_ptr *tmp
    count[0] = len(lst)
    tmp = <const_char_ptr*>calloc(sizeof(char*), count[0])
    for idx, x in enumerate(lst):
        tmp[idx] = x
    res[0] = tmp

cdef _list_to_str_array(lst, const_char_ptr **res, int *count):
    cdef const_char_ptr *tmp
    count[0] = len(lst)
    tmp = <const_char_ptr*>calloc(sizeof(char*), count[0])
    new_objs = []
    for idx, x in enumerate(lst):
        if isinstance(x, unicode):
            x = x.encode('utf-8')
            new_objs.append(x)
        tmp[idx] = x
    res[0] = tmp
    return new_objs


cdef int _append_index_definition_to_list(void *context,
        const_char_ptr index_name, int n_expressions,
        const_char_ptr *expressions) with gil:
    cdef int i

    a_list = <object>(context)
    exp_list = []
    for i from 0 <= i < n_expressions:
        s = expressions[i]
        exp_list.append(s.decode('utf-8'))
    a_list.append((index_name, exp_list))
    return 0


cdef int return_doc_cb_wrapper(void *context, u1db_document *doc,
                               int gen, const_char_ptr trans_id) with gil:
    cdef CDocument pydoc
    user_cb = <object>context
    pydoc = CDocument()
    pydoc._doc = doc
    try:
        user_cb(pydoc, gen, trans_id)
    except Exception, e:
        # We suppress the exception here, because intermediating through the C
        # layer gets a bit crazy
        return U1DB_INVALID_PARAMETER
    return U1DB_OK


cdef int _trace_hook(void *context, const_char_ptr state) with gil:
    if context == NULL:
        return U1DB_INVALID_PARAMETER
    ctx = <object>context
    try:
        ctx(state)
    except:
        # Note: It would be nice if we could map the Python exception into
        #       something in C
        return U1DB_INTERNAL_ERROR
    return U1DB_OK


cdef char *_ensure_str(object obj, object extra_objs) except NULL:
    """Ensure that we have the UTF-8 representation of a parameter.

    :param obj: A Unicode or String object.
    :param extra_objs: This should be a Python list. If we have to convert obj
        from being a Unicode object, this will hold the PyString object so that
        we know the char* lifetime will be correct.
    :return: A C pointer to the UTF-8 representation.
    """
    if isinstance(obj, unicode):
        obj = obj.encode('utf-8')
        extra_objs.append(obj)
    return PyString_AsString(obj)


def _format_query(fields):
    """Wrapper around u1db__format_query for testing."""
    cdef int status
    cdef char *buf
    cdef int wildcard[10]
    cdef const_char_ptr *values
    cdef int n_values

    # keep a reference to new_objs so that the pointers in expressions
    # remain valid.
    new_objs = _list_to_str_array(fields, &values, &n_values)
    try:
        status = u1db__format_query(n_values, values, &buf, wildcard)
    finally:
        free(<void*>values)
    handle_status("format_query", status)
    if buf == NULL:
        res = None
    else:
        res = buf
        free(buf)
    w = []
    for i in range(len(fields)):
        w.append(wildcard[i])
    return res, w


def make_document(doc_id, rev, content, has_conflicts=False):
    cdef u1db_document *doc
    cdef char *c_content = NULL, *c_rev = NULL, *c_doc_id = NULL
    cdef int conflict

    if has_conflicts:
        conflict = 1
    else:
        conflict = 0
    if doc_id is None:
        c_doc_id = NULL
    else:
        c_doc_id = doc_id
    if content is None:
        c_content = NULL
    else:
        c_content = content
    if rev is None:
        c_rev = NULL
    else:
        c_rev = rev
    handle_status(
        "make_document",
        u1db__allocate_document(c_doc_id, c_rev, c_content, conflict, &doc))
    pydoc = CDocument()
    pydoc._doc = doc
    return pydoc


def generate_hex_uuid():
    uuid = PyString_FromStringAndSize(NULL, 32)
    handle_status(
        "Failed to generate uuid",
        u1db__generate_hex_uuid(PyString_AS_STRING(uuid)))
    return uuid


cdef class CDocument(object):
    """A thin wrapper around the C Document struct."""

    cdef u1db_document *_doc

    def __init__(self):
        self._doc = NULL

    def __dealloc__(self):
        u1db_free_doc(&self._doc)

    property doc_id:
        def __get__(self):
            if self._doc.doc_id == NULL:
                return None
            return PyString_FromStringAndSize(
                    self._doc.doc_id, self._doc.doc_id_len)

    property rev:
        def __get__(self):
            if self._doc.doc_rev == NULL:
                return None
            return PyString_FromStringAndSize(
                    self._doc.doc_rev, self._doc.doc_rev_len)

    def get_json(self):
        if self._doc.json == NULL:
            return None
        return PyString_FromStringAndSize(
                self._doc.json, self._doc.json_len)

    def set_json(self, val):
        u1db_doc_set_json(self._doc, val)

    def get_size(self):
        return u1db_doc_get_size(self._doc)

    property has_conflicts:
        def __get__(self):
            if self._doc.has_conflicts:
                return True
            return False

    def __repr__(self):
        if self._doc.has_conflicts:
            extra = ', conflicted'
        else:
            extra = ''
        return '%s(%s, %s%s, %r)' % (self.__class__.__name__, self.doc_id,
                                     self.rev, extra, self.get_json())

    def __hash__(self):
        raise NotImplementedError(self.__hash__)

    def __richcmp__(self, other, int t):
        try:
            if t == 0: # Py_LT <
                return ((self.doc_id, self.rev, self.get_json())
                    < (other.doc_id, other.rev, other.get_json()))
            elif t == 2: # Py_EQ ==
                return (self.doc_id == other.doc_id
                        and self.rev == other.rev
                        and self.get_json() == other.get_json()
                        and self.has_conflicts == other.has_conflicts)
        except AttributeError:
            # Fall through to NotImplemented
            pass

        return NotImplemented


cdef object safe_str(const_char_ptr s):
    if s == NULL:
        return None
    return s


cdef class CQuery:

    cdef u1query *_query

    def __init__(self):
        self._query = NULL

    def __dealloc__(self):
        u1db_free_query(&self._query)

    def _check(self):
        if self._query == NULL:
            raise RuntimeError("No valid _query.")

    property index_name:
        def __get__(self):
            self._check()
            return safe_str(self._query.index_name)

    property num_fields:
        def __get__(self):
            self._check()
            return self._query.num_fields

    property fields:
        def __get__(self):
            cdef int i
            self._check()
            fields = []
            for i from 0 <= i < self._query.num_fields:
                fields.append(safe_str(self._query.fields[i]))
            return fields


cdef handle_status(context, int status):
    if status == U1DB_OK:
        return
    if status == U1DB_REVISION_CONFLICT:
        raise errors.RevisionConflict()
    if status == U1DB_INVALID_DOC_ID:
        raise errors.InvalidDocId()
    if status == U1DB_DOCUMENT_ALREADY_DELETED:
        raise errors.DocumentAlreadyDeleted()
    if status == U1DB_DOCUMENT_DOES_NOT_EXIST:
        raise errors.DocumentDoesNotExist()
    if status == U1DB_INVALID_PARAMETER:
        raise RuntimeError('Bad parameters supplied')
    if status == U1DB_NOT_IMPLEMENTED:
        raise NotImplementedError("Functionality not implemented yet: %s"
                                  % (context,))
    if status == U1DB_INVALID_VALUE_FOR_INDEX:
        raise errors.InvalidValueForIndex()
    if status == U1DB_INVALID_GLOBBING:
        raise errors.InvalidGlobbing()
    if status == U1DB_INTERNAL_ERROR:
        raise errors.U1DBError("internal error")
    if status == U1DB_BROKEN_SYNC_STREAM:
        raise errors.BrokenSyncStream()
    if status == U1DB_CONFLICTED:
        raise errors.ConflictedDoc()
    if status == U1DB_DUPLICATE_INDEX_NAME:
        raise errors.IndexNameTakenError()
    if status == U1DB_INDEX_DOES_NOT_EXIST:
        raise errors.IndexDoesNotExist
    if status == U1DB_INVALID_GENERATION:
        raise errors.InvalidGeneration
    if status == U1DB_INVALID_TRANSACTION_ID:
        raise errors.InvalidTransactionId
    if status == U1DB_TARGET_UNAVAILABLE:
        raise errors.Unavailable
    if status == U1DB_INVALID_JSON:
        raise errors.InvalidJSON
    if status == U1DB_DOCUMENT_TOO_BIG:
        raise errors.DocumentTooBig
    if status == U1DB_USER_QUOTA_EXCEEDED:
        raise errors.UserQuotaExceeded
    if status == U1DB_INVALID_TRANSFORMATION_FUNCTION:
        raise errors.IndexDefinitionParseError
    if status == U1DB_UNKNOWN_OPERATION:
        raise errors.IndexDefinitionParseError
    if status == U1DB_INVALID_FIELD_SPECIFIER:
        raise errors.IndexDefinitionParseError()
    raise RuntimeError('%s (status: %s)' % (context, status))


cdef class CDatabase
cdef class CSyncTarget

cdef class CSyncExchange(object):

    cdef u1db_sync_exchange *_exchange
    cdef CSyncTarget _target

    def __init__(self, CSyncTarget target, source_replica_uid, source_gen):
        self._target = target
        assert self._target._st.get_sync_exchange != NULL, \
                "get_sync_exchange is NULL?"
        handle_status("get_sync_exchange",
            self._target._st.get_sync_exchange(self._target._st,
                source_replica_uid, source_gen, &self._exchange))

    def __dealloc__(self):
        if self._target is not None and self._target._st != NULL:
            self._target._st.finalize_sync_exchange(self._target._st,
                    &self._exchange)

    def _check(self):
        if self._exchange == NULL:
            raise RuntimeError("self._exchange is NULL")

    property target_gen:
        def __get__(self):
            self._check()
            return self._exchange.target_gen

    def insert_doc_from_source(self, CDocument doc, source_gen,
                               source_trans_id):
        self._check()
        handle_status("insert_doc_from_source",
            u1db__sync_exchange_insert_doc_from_source(self._exchange,
                doc._doc, source_gen, source_trans_id))

    def find_doc_ids_to_return(self):
        self._check()
        handle_status("find_doc_ids_to_return",
            u1db__sync_exchange_find_doc_ids_to_return(self._exchange))

    def return_docs(self, return_doc_cb):
        self._check()
        handle_status("return_docs",
            u1db__sync_exchange_return_docs(self._exchange,
                <void *>return_doc_cb, &return_doc_cb_wrapper))

    def get_seen_ids(self):
        cdef const_char_ptr *seen_ids
        cdef int i, n_ids
        self._check()
        handle_status("sync_exchange_seen_ids",
            u1db__sync_exchange_seen_ids(self._exchange, &n_ids, &seen_ids))
        res = []
        for i from 0 <= i < n_ids:
            res.append(seen_ids[i])
        if (seen_ids != NULL):
            free(<void*>seen_ids)
        return res

    def get_doc_ids_to_return(self):
        self._check()
        res = []
        if (self._exchange.num_doc_ids > 0
                and self._exchange.doc_ids_to_return != NULL):
            for i from 0 <= i < self._exchange.num_doc_ids:
                res.append(
                    (self._exchange.doc_ids_to_return[i],
                     self._exchange.gen_for_doc_ids[i],
                     self._exchange.trans_ids_for_doc_ids[i]))
        return res


cdef class CSyncTarget(object):

    cdef u1db_sync_target *_st
    cdef CDatabase _db

    def __init__(self):
        self._db = None
        self._st = NULL
        u1db__set_zero_delays()

    def __dealloc__(self):
        u1db__free_sync_target(&self._st)

    def _check(self):
        if self._st == NULL:
            raise RuntimeError("self._st is NULL")

    def get_sync_info(self, source_replica_uid):
        cdef const_char_ptr st_replica_uid = NULL
        cdef int st_gen = 0, source_gen = 0, status
        cdef char *trans_id = NULL
        cdef char *st_trans_id = NULL
        cdef char *c_source_replica_uid = NULL

        self._check()
        assert self._st.get_sync_info != NULL, "get_sync_info is NULL?"
        c_source_replica_uid = source_replica_uid
        with nogil:
            status = self._st.get_sync_info(self._st, c_source_replica_uid,
                &st_replica_uid, &st_gen, &st_trans_id, &source_gen, &trans_id)
        handle_status("get_sync_info", status)
        res_trans_id = None
        res_st_trans_id = None
        if trans_id != NULL:
            res_trans_id = trans_id
            free(trans_id)
        if st_trans_id != NULL:
            res_st_trans_id = st_trans_id
            free(st_trans_id)
        return (
            safe_str(st_replica_uid), st_gen, res_st_trans_id, source_gen,
            res_trans_id)

    def record_sync_info(self, source_replica_uid, source_gen, source_trans_id):
        cdef int status
        cdef int c_source_gen
        cdef char *c_source_replica_uid = NULL
        cdef char *c_source_trans_id = NULL

        self._check()
        assert self._st.record_sync_info != NULL, "record_sync_info is NULL?"
        c_source_replica_uid = source_replica_uid
        c_source_gen = source_gen
        c_source_trans_id = source_trans_id
        with nogil:
            status = self._st.record_sync_info(
                self._st, c_source_replica_uid, c_source_gen,
                c_source_trans_id)
        handle_status("record_sync_info", status)

    def _get_sync_exchange(self, source_replica_uid, source_gen):
        self._check()
        return CSyncExchange(self, source_replica_uid, source_gen)

    def sync_exchange_doc_ids(self, source_db, doc_id_generations,
                              last_known_generation, last_known_trans_id,
                              return_doc_cb):
        cdef const_char_ptr *doc_ids
        cdef int *generations
        cdef int num_doc_ids
        cdef int target_gen
        cdef char *target_trans_id = NULL
        cdef int status
        cdef CDatabase sdb

        self._check()
        assert self._st.sync_exchange_doc_ids != NULL, "sync_exchange_doc_ids is NULL?"
        sdb = source_db
        num_doc_ids = len(doc_id_generations)
        doc_ids = <const_char_ptr *>calloc(num_doc_ids, sizeof(char *))
        if doc_ids == NULL:
            raise MemoryError
        generations = <int *>calloc(num_doc_ids, sizeof(int))
        if generations == NULL:
            free(<void *>doc_ids)
            raise MemoryError
        trans_ids = <const_char_ptr*>calloc(num_doc_ids, sizeof(char *))
        if trans_ids == NULL:
            raise MemoryError
        res_trans_id = ''
        try:
            for i, (doc_id, gen, trans_id) in enumerate(doc_id_generations):
                doc_ids[i] = PyString_AsString(doc_id)
                generations[i] = gen
                trans_ids[i] = trans_id
            target_gen = last_known_generation
            if last_known_trans_id is not None:
                target_trans_id = last_known_trans_id
            with nogil:
                status = self._st.sync_exchange_doc_ids(self._st, sdb._db,
                    num_doc_ids, doc_ids, generations, trans_ids,
                    &target_gen, &target_trans_id,
                    <void*>return_doc_cb, return_doc_cb_wrapper, NULL)
            handle_status("sync_exchange_doc_ids", status)
            if target_trans_id != NULL:
                res_trans_id = target_trans_id
        finally:
            if target_trans_id != NULL:
                free(target_trans_id)
            if doc_ids != NULL:
                free(<void *>doc_ids)
            if generations != NULL:
                free(generations)
            if trans_ids != NULL:
                free(trans_ids)
        return target_gen, res_trans_id

    def sync_exchange(self, docs_by_generations, source_replica_uid,
                      last_known_generation, last_known_trans_id,
                      return_doc_cb, ensure_callback=None):
        cdef CDocument cur_doc
        cdef u1db_document **docs = NULL
        cdef int *generations = NULL
        cdef const_char_ptr *trans_ids = NULL
        cdef char *target_trans_id = NULL
        cdef char *c_source_replica_uid = NULL
        cdef int i, count, status, target_gen
        assert ensure_callback is None  # interface difference

        self._check()
        assert self._st.sync_exchange != NULL, "sync_exchange is NULL?"
        count = len(docs_by_generations)
        res_trans_id = ''
        try:
            docs = <u1db_document **>calloc(count, sizeof(u1db_document*))
            if docs == NULL:
                raise MemoryError
            generations = <int*>calloc(count, sizeof(int))
            if generations == NULL:
                raise MemoryError
            trans_ids = <const_char_ptr*>calloc(count, sizeof(char*))
            if trans_ids == NULL:
                raise MemoryError
            for i from 0 <= i < count:
                cur_doc = docs_by_generations[i][0]
                generations[i] = docs_by_generations[i][1]
                trans_ids[i] = docs_by_generations[i][2]
                docs[i] = cur_doc._doc
            target_gen = last_known_generation
            if last_known_trans_id is not None:
                target_trans_id = last_known_trans_id
            c_source_replica_uid = source_replica_uid
            with nogil:
                status = self._st.sync_exchange(
                    self._st, c_source_replica_uid, count, docs, generations,
                    trans_ids, &target_gen, &target_trans_id,
                    <void *>return_doc_cb, return_doc_cb_wrapper, NULL)
            handle_status("sync_exchange", status)
        finally:
            if docs != NULL:
                free(docs)
            if generations != NULL:
                free(generations)
            if trans_ids != NULL:
                free(trans_ids)
            if target_trans_id != NULL:
                res_trans_id = target_trans_id
                free(target_trans_id)
        return target_gen, res_trans_id

    def _set_trace_hook(self, cb):
        self._check()
        assert self._st._set_trace_hook != NULL, "_set_trace_hook is NULL?"
        handle_status("_set_trace_hook",
            self._st._set_trace_hook(self._st, <void*>cb, _trace_hook))

    _set_trace_hook_shallow = _set_trace_hook


cdef class CDatabase(object):
    """A thin wrapper/shim to interact with the C implementation.

    Functionality should not be written here. It is only provided as a way to
    expose the C API to the python test suite.
    """

    cdef public object _filename
    cdef u1database *_db
    cdef public object _supports_indexes

    def __init__(self, filename):
        self._supports_indexes = False
        self._filename = filename
        self._db = u1db_open(self._filename)

    def __dealloc__(self):
        u1db_free(&self._db)

    def close(self):
        return u1db__sql_close(self._db)

    def _copy(self, db):
        # DO NOT COPY OR REUSE THIS CODE OUTSIDE TESTS: COPYING U1DB DATABASES IS
        # THE WRONG THING TO DO, THE ONLY REASON WE DO SO HERE IS TO TEST THAT WE
        # CORRECTLY DETECT IT HAPPENING SO THAT WE CAN RAISE ERRORS RATHER THAN
        # CORRUPT USER DATA. USE SYNC INSTEAD, OR WE WILL SEND NINJA TO YOUR
        # HOUSE.
        new_db = CDatabase(':memory:')
        u1db_free(&new_db._db)
        new_db._db = u1db__copy(self._db)
        return new_db

    def _sql_is_open(self):
        if self._db == NULL:
            return True
        return u1db__sql_is_open(self._db)

    property _replica_uid:
        def __get__(self):
            cdef const_char_ptr val
            cdef int status
            status = u1db_get_replica_uid(self._db, &val)
            if status != 0:
                if val != NULL:
                    err = str(val)
                else:
                    err = "<unknown>"
                raise RuntimeError("Failed to get_replica_uid: %d %s"
                                   % (status, err))
            if val == NULL:
                return None
            return str(val)

    def _set_replica_uid(self, replica_uid):
        cdef int status
        status = u1db_set_replica_uid(self._db, replica_uid)
        if status != 0:
            raise RuntimeError('replica_uid could not be set to %s, error: %d'
                               % (replica_uid, status))

    property document_size_limit:
        def __get__(self):
            cdef int limit
            handle_status("document_size_limit",
                u1db__get_document_size_limit(self._db, &limit))
            return limit

    def set_document_size_limit(self, limit):
        cdef int status
        status = u1db_set_document_size_limit(self._db, limit)
        if status != 0:
            raise RuntimeError(
                "document_size_limit could not be set to %d, error: %d",
                (limit, status))

    def _allocate_doc_id(self):
        cdef char *val
        val = u1db__allocate_doc_id(self._db)
        if val == NULL:
            raise RuntimeError("Failed to allocate document id")
        s = str(val)
        free(val)
        return s

    def _run_sql(self, sql):
        cdef u1db_table *tbl
        cdef u1db_row *cur_row
        cdef size_t n
        cdef int i

        if self._db == NULL:
            raise RuntimeError("called _run_sql with a NULL pointer.")
        tbl = u1db__sql_run(self._db, sql, len(sql))
        if tbl == NULL:
            raise MemoryError("Failed to allocate table memory.")
        try:
            if tbl.status != 0:
                raise RuntimeError("Status was not 0: %d" % (tbl.status,))
            # Now convert the table into python
            res = []
            cur_row = tbl.first_row
            while cur_row != NULL:
                row = []
                for i from 0 <= i < cur_row.num_columns:
                    row.append(PyString_FromStringAndSize(
                        <char*>(cur_row.columns[i]), cur_row.column_sizes[i]))
                res.append(tuple(row))
                cur_row = cur_row.next
            return res
        finally:
            u1db__free_table(&tbl)

    def create_doc_from_json(self, json, doc_id=None):
        cdef u1db_document *doc = NULL
        cdef char *c_doc_id

        if doc_id is None:
            c_doc_id = NULL
        else:
            c_doc_id = doc_id
        handle_status('Failed to create_doc',
            u1db_create_doc_from_json(self._db, json, c_doc_id, &doc))
        pydoc = CDocument()
        pydoc._doc = doc
        return pydoc

    def put_doc(self, CDocument doc):
        handle_status("Failed to put_doc",
            u1db_put_doc(self._db, doc._doc))
        return doc.rev

    def _validate_source(self, replica_uid, replica_gen, replica_trans_id):
        cdef const_char_ptr c_uid, c_trans_id
        cdef int c_gen = 0

        c_uid = replica_uid
        c_trans_id = replica_trans_id
        c_gen = replica_gen
        handle_status(
            "invalid generation or transaction id",
            u1db__validate_source(self._db, c_uid, c_gen, c_trans_id))

    def _put_doc_if_newer(self, CDocument doc, save_conflict, replica_uid=None,
                          replica_gen=None, replica_trans_id=None):
        cdef char *c_uid, *c_trans_id
        cdef int gen, state = 0, at_gen = -1

        if replica_uid is None:
            c_uid = NULL
        else:
            c_uid = replica_uid
        if replica_trans_id is None:
            c_trans_id = NULL
        else:
            c_trans_id = replica_trans_id
        if replica_gen is None:
            gen = 0
        else:
            gen = replica_gen
        handle_status("Failed to _put_doc_if_newer",
            u1db__put_doc_if_newer(self._db, doc._doc, save_conflict,
                c_uid, gen, c_trans_id, &state, &at_gen))
        if state == U1DB_INSERTED:
            return 'inserted', at_gen
        elif state == U1DB_SUPERSEDED:
            return 'superseded', at_gen
        elif state == U1DB_CONVERGED:
            return 'converged', at_gen
        elif state == U1DB_CONFLICTED:
            return 'conflicted', at_gen
        else:
            raise RuntimeError("Unknown _put_doc_if_newer state: %d" % (state,))

    def get_doc(self, doc_id, include_deleted=False):
        cdef u1db_document *doc = NULL
        deleted = 1 if include_deleted else 0
        handle_status("get_doc failed",
            u1db_get_doc(self._db, doc_id, deleted, &doc))
        if doc == NULL:
            return None
        pydoc = CDocument()
        pydoc._doc = doc
        return pydoc

    def get_docs(self, doc_ids, check_for_conflicts=True,
                 include_deleted=False):
        cdef int n_doc_ids, conflicts
        cdef const_char_ptr *c_doc_ids

        _list_to_array(doc_ids, &c_doc_ids, &n_doc_ids)
        deleted = 1 if include_deleted else 0
        conflicts = 1 if check_for_conflicts else 0
        a_list = []
        handle_status("get_docs",
            u1db_get_docs(self._db, n_doc_ids, c_doc_ids,
                conflicts, deleted, <void*>a_list, _append_doc_to_list))
        free(<void*>c_doc_ids)
        return a_list

    def get_all_docs(self, include_deleted=False):
        cdef int c_generation

        a_list = []
        deleted = 1 if include_deleted else 0
        generation = 0
        c_generation = generation
        handle_status(
            "get_all_docs", u1db_get_all_docs(
                self._db, deleted, &c_generation, <void*>a_list,
                _append_doc_to_list))
        return (c_generation, a_list)

    def resolve_doc(self, CDocument doc, conflicted_doc_revs):
        cdef const_char_ptr *revs
        cdef int n_revs

        _list_to_array(conflicted_doc_revs, &revs, &n_revs)
        handle_status("resolve_doc",
            u1db_resolve_doc(self._db, doc._doc, n_revs, revs))
        free(<void*>revs)

    def get_doc_conflicts(self, doc_id):
        conflict_docs = []
        handle_status("get_doc_conflicts",
            u1db_get_doc_conflicts(self._db, doc_id, <void*>conflict_docs,
                _append_doc_to_list))
        return conflict_docs

    def delete_doc(self, CDocument doc):
        handle_status(
            "Failed to delete %s" % (doc,),
            u1db_delete_doc(self._db, doc._doc))

    def whats_changed(self, generation=0):
        cdef int c_generation
        cdef int status
        cdef char *trans_id = NULL

        a_list = []
        c_generation = generation
        res_trans_id = ''
        status = u1db_whats_changed(self._db, &c_generation, &trans_id,
                                    <void*>a_list, _append_trans_info_to_list)
        try:
            handle_status("whats_changed", status)
        finally:
            if trans_id != NULL:
                res_trans_id = trans_id
                free(trans_id)
        return c_generation, res_trans_id, a_list

    def _get_transaction_log(self):
        a_list = []
        handle_status("_get_transaction_log",
            u1db__get_transaction_log(self._db, <void*>a_list,
                                      _append_trans_info_to_list))
        return [(doc_id, trans_id) for doc_id, gen, trans_id in a_list]

    def _get_generation(self):
        cdef int generation
        handle_status("get_generation",
            u1db__get_generation(self._db, &generation))
        return generation

    def _get_generation_info(self):
        cdef int generation
        cdef char *trans_id
        handle_status("get_generation_info",
            u1db__get_generation_info(self._db, &generation, &trans_id))
        raw_trans_id = None
        if trans_id != NULL:
            raw_trans_id = trans_id
            free(trans_id)
        return generation, raw_trans_id

    def validate_gen_and_trans_id(self, generation, trans_id):
        handle_status(
            "validate_gen_and_trans_id",
            u1db_validate_gen_and_trans_id(self._db, generation, trans_id))

    def _get_trans_id_for_gen(self, generation):
        cdef char *trans_id = NULL

        handle_status(
            "_get_trans_id_for_gen",
            u1db__get_trans_id_for_gen(self._db, generation, &trans_id))
        raw_trans_id = None
        if trans_id != NULL:
            raw_trans_id = trans_id
            free(trans_id)
        return raw_trans_id

    def _get_replica_gen_and_trans_id(self, replica_uid):
        cdef int generation, status
        cdef char *trans_id = NULL

        status = u1db__get_replica_gen_and_trans_id(
            self._db, replica_uid, &generation, &trans_id)
        handle_status("_get_replica_gen_and_trans_id", status)
        raw_trans_id = None
        if trans_id != NULL:
            raw_trans_id = trans_id
            free(trans_id)
        return generation, raw_trans_id

    def _set_replica_gen_and_trans_id(self, replica_uid, generation, trans_id):
        handle_status("_set_replica_gen_and_trans_id",
            u1db__set_replica_gen_and_trans_id(
                self._db, replica_uid, generation, trans_id))

    def create_index_list(self, index_name, index_expressions):
        cdef const_char_ptr *expressions
        cdef int n_expressions

        # keep a reference to new_objs so that the pointers in expressions
        # remain valid.
        new_objs = _list_to_str_array(
            index_expressions, &expressions, &n_expressions)
        try:
            status = u1db_create_index_list(
                self._db, index_name, n_expressions, expressions)
        finally:
            free(<void*>expressions)
        handle_status("create_index", status)

    def create_index(self, index_name, *index_expressions):
        extra = []
        if len(index_expressions) == 0:
            status = u1db_create_index(self._db, index_name, 0, NULL)
        elif len(index_expressions) == 1:
            status = u1db_create_index(
                self._db, index_name, 1,
                _ensure_str(index_expressions[0], extra))
        elif len(index_expressions) == 2:
            status = u1db_create_index(
                self._db, index_name, 2,
                _ensure_str(index_expressions[0], extra),
                _ensure_str(index_expressions[1], extra))
        elif len(index_expressions) == 3:
            status = u1db_create_index(
                self._db, index_name, 3,
                _ensure_str(index_expressions[0], extra),
                _ensure_str(index_expressions[1], extra),
                _ensure_str(index_expressions[2], extra))
        elif len(index_expressions) == 4:
            status = u1db_create_index(
                self._db, index_name, 4,
                _ensure_str(index_expressions[0], extra),
                _ensure_str(index_expressions[1], extra),
                _ensure_str(index_expressions[2], extra),
                _ensure_str(index_expressions[3], extra))
        else:
            status = U1DB_NOT_IMPLEMENTED
        handle_status("create_index", status)

    def sync(self, url, creds=None):
        cdef const_char_ptr c_url
        cdef int local_gen = 0
        cdef u1db_oauth_creds _oauth_creds
        cdef u1db_creds *_creds = NULL
        c_url = url
        if creds is not None:
            _oauth_creds.auth_kind = U1DB_OAUTH_AUTH
            _oauth_creds.consumer_key = creds['oauth']['consumer_key']
            _oauth_creds.consumer_secret = creds['oauth']['consumer_secret']
            _oauth_creds.token_key = creds['oauth']['token_key']
            _oauth_creds.token_secret = creds['oauth']['token_secret']
            _creds = <u1db_creds *>&_oauth_creds
        with nogil:
            status = u1db_sync(self._db, c_url, _creds, &local_gen)
        handle_status("sync", status)
        return local_gen

    def list_indexes(self):
        a_list = []
        handle_status("list_indexes",
            u1db_list_indexes(self._db, <void *>a_list,
                              _append_index_definition_to_list))
        return a_list

    def delete_index(self, index_name):
        handle_status("delete_index",
            u1db_delete_index(self._db, index_name))

    def get_from_index_list(self, index_name, key_values):
        cdef const_char_ptr *values
        cdef int n_values
        cdef CQuery query

        query = self._query_init(index_name)
        res = []
        # keep a reference to new_objs so that the pointers in expressions
        # remain valid.
        new_objs = _list_to_str_array(key_values, &values, &n_values)
        try:
            handle_status(
                "get_from_index", u1db_get_from_index_list(
                    self._db, query._query, <void*>res, _append_doc_to_list,
                    n_values, values))
        finally:
            free(<void*>values)
        return res

    def get_from_index(self, index_name, *key_values):
        cdef CQuery query
        cdef int status

        extra = []
        query = self._query_init(index_name)
        res = []
        status = U1DB_OK
        if len(key_values) == 0:
            status = u1db_get_from_index(self._db, query._query,
                <void*>res, _append_doc_to_list, 0, NULL)
        elif len(key_values) == 1:
            status = u1db_get_from_index(self._db, query._query,
                <void*>res, _append_doc_to_list, 1,
                _ensure_str(key_values[0], extra))
        elif len(key_values) == 2:
            status = u1db_get_from_index(self._db, query._query,
                <void*>res, _append_doc_to_list, 2,
                _ensure_str(key_values[0], extra),
                _ensure_str(key_values[1], extra))
        elif len(key_values) == 3:
            status = u1db_get_from_index(self._db, query._query,
                <void*>res, _append_doc_to_list, 3,
                _ensure_str(key_values[0], extra),
                _ensure_str(key_values[1], extra),
                _ensure_str(key_values[2], extra))
        elif len(key_values) == 4:
            status = u1db_get_from_index(self._db, query._query,
                <void*>res, _append_doc_to_list, 4,
                _ensure_str(key_values[0], extra),
                _ensure_str(key_values[1], extra),
                _ensure_str(key_values[2], extra),
                _ensure_str(key_values[3], extra))
        else:
            status = U1DB_NOT_IMPLEMENTED
        handle_status("get_from_index", status)
        return res

    def get_range_from_index(self, index_name, start_value=None,
                             end_value=None):
        cdef CQuery query
        cdef const_char_ptr *start_values
        cdef int n_values
        cdef const_char_ptr *end_values

        if start_value is not None:
            if isinstance(start_value, basestring):
                start_value = (start_value,)
            new_objs_1 = _list_to_str_array(
                start_value, &start_values, &n_values)
        else:
            n_values = 0
            start_values = NULL
        if end_value is not None:
            if isinstance(end_value, basestring):
                end_value = (end_value,)
            new_objs_2 = _list_to_str_array(
                end_value, &end_values, &n_values)
        else:
            end_values = NULL
        query = self._query_init(index_name)
        res = []
        try:
            handle_status("get_range_from_index",
                u1db_get_range_from_index(
                    self._db, query._query, <void*>res, _append_doc_to_list,
                    n_values, start_values, end_values))
        finally:
            if start_values != NULL:
                free(<void*>start_values)
            if end_values != NULL:
                free(<void*>end_values)
        return res

    def get_index_keys(self, index_name):
        cdef int status
        keys = []
        status = U1DB_OK
        status = u1db_get_index_keys(
            self._db, index_name, <void*>keys, _append_key_to_list)
        handle_status("get_index_keys", status)
        return keys

    def _query_init(self, index_name):
        cdef CQuery query
        query = CQuery()
        handle_status("query_init",
            u1db_query_init(self._db, index_name, &query._query))
        return query

    def get_sync_target(self):
        cdef CSyncTarget target
        target = CSyncTarget()
        target._db = self
        handle_status("get_sync_target",
            u1db__get_sync_target(target._db._db, &target._st))
        return target


cdef class VectorClockRev:

    cdef u1db_vectorclock *_clock

    def __init__(self, s):
        if s is None:
            self._clock = u1db__vectorclock_from_str(NULL)
        else:
            self._clock = u1db__vectorclock_from_str(s)

    def __dealloc__(self):
        u1db__free_vectorclock(&self._clock)

    def __repr__(self):
        cdef int status
        cdef char *res
        if self._clock == NULL:
            return '%s(None)' % (self.__class__.__name__,)
        status = u1db__vectorclock_as_str(self._clock, &res)
        if status != U1DB_OK:
            return '%s(<failure: %d>)' % (status,)
        if res == NULL:
            val = '%s(NULL)' % (self.__class__.__name__,)
        else:
            val = '%s(%s)' % (self.__class__.__name__, res)
            free(res)
        return val

    def as_dict(self):
        cdef u1db_vectorclock *cur
        cdef int i
        cdef int gen
        if self._clock == NULL:
            return None
        res = {}
        for i from 0 <= i < self._clock.num_items:
            gen = self._clock.items[i].generation
            res[self._clock.items[i].replica_uid] = gen
        return res

    def as_str(self):
        cdef int status
        cdef char *res

        status = u1db__vectorclock_as_str(self._clock, &res)
        if status != U1DB_OK:
            raise RuntimeError("Failed to VectorClockRev.as_str(): %d" % (status,))
        if res == NULL:
            s = None
        else:
            s = res
            free(res)
        return s

    def increment(self, replica_uid):
        cdef int status

        status = u1db__vectorclock_increment(self._clock, replica_uid)
        if status != U1DB_OK:
            raise RuntimeError("Failed to increment: %d" % (status,))

    def maximize(self, vcr):
        cdef int status
        cdef VectorClockRev other

        other = vcr
        status = u1db__vectorclock_maximize(self._clock, other._clock)
        if status != U1DB_OK:
            raise RuntimeError("Failed to maximize: %d" % (status,))

    def is_newer(self, vcr):
        cdef int is_newer
        cdef VectorClockRev other

        other = vcr
        is_newer = u1db__vectorclock_is_newer(self._clock, other._clock)
        if is_newer == 0:
            return False
        elif is_newer == 1:
            return True
        else:
            raise RuntimeError("Failed to is_newer: %d" % (is_newer,))


def sync_db_to_target(db, target):
    """Sync the data between a CDatabase and a CSyncTarget"""
    cdef CDatabase cdb
    cdef CSyncTarget ctarget
    cdef int local_gen = 0, status

    cdb = db
    ctarget = target
    with nogil:
        status = u1db__sync_db_to_target(cdb._db, ctarget._st, &local_gen)
    handle_status("sync_db_to_target", status)
    return local_gen


def create_http_sync_target(url):
    cdef CSyncTarget target

    target = CSyncTarget()
    handle_status("create_http_sync_target",
        u1db__create_http_sync_target(url, &target._st))
    return target


def create_oauth_http_sync_target(url, consumer_key, consumer_secret,
                                  token_key, token_secret):
    cdef CSyncTarget target

    target = CSyncTarget()
    handle_status("create_http_sync_target",
        u1db__create_oauth_http_sync_target(url, consumer_key, consumer_secret,
                                            token_key, token_secret,
                                            &target._st))
    return target


def _format_sync_url(target, source_replica_uid):
    cdef CSyncTarget st
    cdef char *sync_url = NULL
    cdef object res
    st = target
    handle_status("format_sync_url",
        u1db__format_sync_url(st._st, source_replica_uid, &sync_url))
    if sync_url == NULL:
        res = None
    else:
        res = sync_url
        free(sync_url)
    return res


def _get_oauth_authorization(target, method, url):
    cdef CSyncTarget st
    cdef char *auth = NULL

    st = target
    handle_status("get_oauth_authorization",
        u1db__get_oauth_authorization(st._st, method, url, &auth))
    res = None
    if auth != NULL:
        res = auth
        free(auth)
    return res
