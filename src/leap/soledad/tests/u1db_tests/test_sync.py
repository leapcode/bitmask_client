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

"""The Synchronization class for U1DB."""

import os
from wsgiref import simple_server

from u1db import (
    errors,
    sync,
    vectorclock,
    SyncTarget,
    )

from leap.soledad.tests import u1db_tests as tests

from u1db.backends import (
    inmemory,
    )
from u1db.remote import (
    http_target,
    )

from leap.soledad.tests.u1db_tests.test_remote_sync_target import (
    make_http_app,
    make_oauth_http_app,
    )

simple_doc = tests.simple_doc
nested_doc = tests.nested_doc


def _make_local_db_and_target(test):
    db = test.create_database('test')
    st = db.get_sync_target()
    return db, st


def _make_local_db_and_http_target(test, path='test'):
    test.startServer()
    db = test.request_state._create_database(os.path.basename(path))
    st = http_target.HTTPSyncTarget.connect(test.getURL(path))
    return db, st


def _make_local_db_and_oauth_http_target(test):
    db, st = _make_local_db_and_http_target(test, '~/test')
    st.set_oauth_credentials(tests.consumer1.key, tests.consumer1.secret,
                             tests.token1.key, tests.token1.secret)
    return db, st


target_scenarios = [
    ('local', {'create_db_and_target': _make_local_db_and_target}),
    ('http', {'create_db_and_target': _make_local_db_and_http_target,
              'make_app_with_state': make_http_app}),
    ('oauth_http', {'create_db_and_target':
                    _make_local_db_and_oauth_http_target,
                    'make_app_with_state': make_oauth_http_app}),
    ]


class DatabaseSyncTargetTests(tests.DatabaseBaseTests,
                              tests.TestCaseWithServer):

    scenarios = (tests.multiply_scenarios(tests.DatabaseBaseTests.scenarios,
                                          target_scenarios))
                 #+ c_db_scenarios)
    # whitebox true means self.db is the actual local db object
    # against which the sync is performed
    whitebox = True

    def setUp(self):
        super(DatabaseSyncTargetTests, self).setUp()
        self.db, self.st = self.create_db_and_target(self)
        self.other_changes = []

    def tearDown(self):
        # We delete them explicitly, so that connections are cleanly closed
        del self.st
        self.db.close()
        del self.db
        super(DatabaseSyncTargetTests, self).tearDown()

    def receive_doc(self, doc, gen, trans_id):
        self.other_changes.append(
            (doc.doc_id, doc.rev, doc.get_json(), gen, trans_id))

    def set_trace_hook(self, callback, shallow=False):
        setter = (self.st._set_trace_hook if not shallow else
                  self.st._set_trace_hook_shallow)
        try:
            setter(callback)
        except NotImplementedError:
            self.skipTest("%s does not implement _set_trace_hook"
                          % (self.st.__class__.__name__,))

    def test_get_sync_target(self):
        self.assertIsNot(None, self.st)

    def test_get_sync_info(self):
        self.assertEqual(
            ('test', 0, '', 0, ''), self.st.get_sync_info('other'))

    def test_create_doc_updates_sync_info(self):
        self.assertEqual(
            ('test', 0, '', 0, ''), self.st.get_sync_info('other'))
        self.db.create_doc_from_json(simple_doc)
        self.assertEqual(1, self.st.get_sync_info('other')[1])

    def test_record_sync_info(self):
        self.st.record_sync_info('replica', 10, 'T-transid')
        self.assertEqual(
            ('test', 0, '', 10, 'T-transid'), self.st.get_sync_info('replica'))

    def test_sync_exchange(self):
        docs_by_gen = [
            (self.make_document('doc-id', 'replica:1', simple_doc), 10,
             'T-sid')]
        new_gen, trans_id = self.st.sync_exchange(
            docs_by_gen, 'replica', last_known_generation=0,
            last_known_trans_id=None, return_doc_cb=self.receive_doc)
        self.assertGetDoc(self.db, 'doc-id', 'replica:1', simple_doc, False)
        self.assertTransactionLog(['doc-id'], self.db)
        last_trans_id = self.getLastTransId(self.db)
        self.assertEqual(([], 1, last_trans_id),
                         (self.other_changes, new_gen, last_trans_id))
        self.assertEqual(10, self.st.get_sync_info('replica')[3])

    def test_sync_exchange_deleted(self):
        doc = self.db.create_doc_from_json('{}')
        edit_rev = 'replica:1|' + doc.rev
        docs_by_gen = [
            (self.make_document(doc.doc_id, edit_rev, None), 10, 'T-sid')]
        new_gen, trans_id = self.st.sync_exchange(
            docs_by_gen, 'replica', last_known_generation=0,
            last_known_trans_id=None, return_doc_cb=self.receive_doc)
        self.assertGetDocIncludeDeleted(
            self.db, doc.doc_id, edit_rev, None, False)
        self.assertTransactionLog([doc.doc_id, doc.doc_id], self.db)
        last_trans_id = self.getLastTransId(self.db)
        self.assertEqual(([], 2, last_trans_id),
                         (self.other_changes, new_gen, trans_id))
        self.assertEqual(10, self.st.get_sync_info('replica')[3])

    def test_sync_exchange_push_many(self):
        docs_by_gen = [
            (self.make_document('doc-id', 'replica:1', simple_doc), 10, 'T-1'),
            (self.make_document('doc-id2', 'replica:1', nested_doc), 11,
             'T-2')]
        new_gen, trans_id = self.st.sync_exchange(
            docs_by_gen, 'replica', last_known_generation=0,
            last_known_trans_id=None, return_doc_cb=self.receive_doc)
        self.assertGetDoc(self.db, 'doc-id', 'replica:1', simple_doc, False)
        self.assertGetDoc(self.db, 'doc-id2', 'replica:1', nested_doc, False)
        self.assertTransactionLog(['doc-id', 'doc-id2'], self.db)
        last_trans_id = self.getLastTransId(self.db)
        self.assertEqual(([], 2, last_trans_id),
                         (self.other_changes, new_gen, trans_id))
        self.assertEqual(11, self.st.get_sync_info('replica')[3])

    def test_sync_exchange_refuses_conflicts(self):
        doc = self.db.create_doc_from_json(simple_doc)
        self.assertTransactionLog([doc.doc_id], self.db)
        new_doc = '{"key": "altval"}'
        docs_by_gen = [
            (self.make_document(doc.doc_id, 'replica:1', new_doc), 10,
             'T-sid')]
        new_gen, _ = self.st.sync_exchange(
            docs_by_gen, 'replica', last_known_generation=0,
            last_known_trans_id=None, return_doc_cb=self.receive_doc)
        self.assertTransactionLog([doc.doc_id], self.db)
        self.assertEqual(
            (doc.doc_id, doc.rev, simple_doc, 1), self.other_changes[0][:-1])
        self.assertEqual(1, new_gen)
        if self.whitebox:
            self.assertEqual(self.db._last_exchange_log['return'],
                             {'last_gen': 1, 'docs': [(doc.doc_id, doc.rev)]})

    def test_sync_exchange_ignores_convergence(self):
        doc = self.db.create_doc_from_json(simple_doc)
        self.assertTransactionLog([doc.doc_id], self.db)
        gen, txid = self.db._get_generation_info()
        docs_by_gen = [
            (self.make_document(doc.doc_id, doc.rev, simple_doc), 10, 'T-sid')]
        new_gen, _ = self.st.sync_exchange(
            docs_by_gen, 'replica', last_known_generation=gen,
            last_known_trans_id=txid, return_doc_cb=self.receive_doc)
        self.assertTransactionLog([doc.doc_id], self.db)
        self.assertEqual(([], 1), (self.other_changes, new_gen))

    def test_sync_exchange_returns_new_docs(self):
        doc = self.db.create_doc_from_json(simple_doc)
        self.assertTransactionLog([doc.doc_id], self.db)
        new_gen, _ = self.st.sync_exchange(
            [], 'other-replica', last_known_generation=0,
            last_known_trans_id=None, return_doc_cb=self.receive_doc)
        self.assertTransactionLog([doc.doc_id], self.db)
        self.assertEqual(
            (doc.doc_id, doc.rev, simple_doc, 1), self.other_changes[0][:-1])
        self.assertEqual(1, new_gen)
        if self.whitebox:
            self.assertEqual(self.db._last_exchange_log['return'],
                             {'last_gen': 1, 'docs': [(doc.doc_id, doc.rev)]})

    def test_sync_exchange_returns_deleted_docs(self):
        doc = self.db.create_doc_from_json(simple_doc)
        self.db.delete_doc(doc)
        self.assertTransactionLog([doc.doc_id, doc.doc_id], self.db)
        new_gen, _ = self.st.sync_exchange(
            [], 'other-replica', last_known_generation=0,
            last_known_trans_id=None, return_doc_cb=self.receive_doc)
        self.assertTransactionLog([doc.doc_id, doc.doc_id], self.db)
        self.assertEqual(
            (doc.doc_id, doc.rev, None, 2), self.other_changes[0][:-1])
        self.assertEqual(2, new_gen)
        if self.whitebox:
            self.assertEqual(self.db._last_exchange_log['return'],
                             {'last_gen': 2, 'docs': [(doc.doc_id, doc.rev)]})

    def test_sync_exchange_returns_many_new_docs(self):
        doc = self.db.create_doc_from_json(simple_doc)
        doc2 = self.db.create_doc_from_json(nested_doc)
        self.assertTransactionLog([doc.doc_id, doc2.doc_id], self.db)
        new_gen, _ = self.st.sync_exchange(
            [], 'other-replica', last_known_generation=0,
            last_known_trans_id=None, return_doc_cb=self.receive_doc)
        self.assertTransactionLog([doc.doc_id, doc2.doc_id], self.db)
        self.assertEqual(2, new_gen)
        self.assertEqual(
            [(doc.doc_id, doc.rev, simple_doc, 1),
             (doc2.doc_id, doc2.rev, nested_doc, 2)],
            [c[:-1] for c in self.other_changes])
        if self.whitebox:
            self.assertEqual(
                self.db._last_exchange_log['return'],
                {'last_gen': 2, 'docs':
                 [(doc.doc_id, doc.rev), (doc2.doc_id, doc2.rev)]})

    def test_sync_exchange_getting_newer_docs(self):
        doc = self.db.create_doc_from_json(simple_doc)
        self.assertTransactionLog([doc.doc_id], self.db)
        new_doc = '{"key": "altval"}'
        docs_by_gen = [
            (self.make_document(doc.doc_id, 'test:1|z:2', new_doc), 10,
             'T-sid')]
        new_gen, _ = self.st.sync_exchange(
            docs_by_gen, 'other-replica', last_known_generation=0,
            last_known_trans_id=None, return_doc_cb=self.receive_doc)
        self.assertTransactionLog([doc.doc_id, doc.doc_id], self.db)
        self.assertEqual(([], 2), (self.other_changes, new_gen))

    def test_sync_exchange_with_concurrent_updates_of_synced_doc(self):
        expected = []

        def before_whatschanged_cb(state):
            if state != 'before whats_changed':
                return
            cont = '{"key": "cuncurrent"}'
            conc_rev = self.db.put_doc(
                self.make_document(doc.doc_id, 'test:1|z:2', cont))
            expected.append((doc.doc_id, conc_rev, cont, 3))

        self.set_trace_hook(before_whatschanged_cb)
        doc = self.db.create_doc_from_json(simple_doc)
        self.assertTransactionLog([doc.doc_id], self.db)
        new_doc = '{"key": "altval"}'
        docs_by_gen = [
            (self.make_document(doc.doc_id, 'test:1|z:2', new_doc), 10,
             'T-sid')]
        new_gen, _ = self.st.sync_exchange(
            docs_by_gen, 'other-replica', last_known_generation=0,
            last_known_trans_id=None, return_doc_cb=self.receive_doc)
        self.assertEqual(expected, [c[:-1] for c in self.other_changes])
        self.assertEqual(3, new_gen)

    def test_sync_exchange_with_concurrent_updates(self):

        def after_whatschanged_cb(state):
            if state != 'after whats_changed':
                return
            self.db.create_doc_from_json('{"new": "doc"}')

        self.set_trace_hook(after_whatschanged_cb)
        doc = self.db.create_doc_from_json(simple_doc)
        self.assertTransactionLog([doc.doc_id], self.db)
        new_doc = '{"key": "altval"}'
        docs_by_gen = [
            (self.make_document(doc.doc_id, 'test:1|z:2', new_doc), 10,
             'T-sid')]
        new_gen, _ = self.st.sync_exchange(
            docs_by_gen, 'other-replica', last_known_generation=0,
            last_known_trans_id=None, return_doc_cb=self.receive_doc)
        self.assertEqual(([], 2), (self.other_changes, new_gen))

    def test_sync_exchange_converged_handling(self):
        doc = self.db.create_doc_from_json(simple_doc)
        docs_by_gen = [
            (self.make_document('new', 'other:1', '{}'), 4, 'T-foo'),
            (self.make_document(doc.doc_id, doc.rev, doc.get_json()), 5,
             'T-bar')]
        new_gen, _ = self.st.sync_exchange(
            docs_by_gen, 'other-replica', last_known_generation=0,
            last_known_trans_id=None, return_doc_cb=self.receive_doc)
        self.assertEqual(([], 2), (self.other_changes, new_gen))

    def test_sync_exchange_detect_incomplete_exchange(self):
        def before_get_docs_explode(state):
            if state != 'before get_docs':
                return
            raise errors.U1DBError("fail")
        self.set_trace_hook(before_get_docs_explode)
        # suppress traceback printing in the wsgiref server
        self.patch(simple_server.ServerHandler,
                   'log_exception', lambda h, exc_info: None)
        doc = self.db.create_doc_from_json(simple_doc)
        self.assertTransactionLog([doc.doc_id], self.db)
        self.assertRaises(
            (errors.U1DBError, errors.BrokenSyncStream),
            self.st.sync_exchange, [], 'other-replica',
            last_known_generation=0, last_known_trans_id=None,
            return_doc_cb=self.receive_doc)

    def test_sync_exchange_doc_ids(self):
        sync_exchange_doc_ids = getattr(self.st, 'sync_exchange_doc_ids', None)
        if sync_exchange_doc_ids is None:
            self.skipTest("sync_exchange_doc_ids not implemented")
        db2 = self.create_database('test2')
        doc = db2.create_doc_from_json(simple_doc)
        new_gen, trans_id = sync_exchange_doc_ids(
            db2, [(doc.doc_id, 10, 'T-sid')], 0, None,
            return_doc_cb=self.receive_doc)
        self.assertGetDoc(self.db, doc.doc_id, doc.rev, simple_doc, False)
        self.assertTransactionLog([doc.doc_id], self.db)
        last_trans_id = self.getLastTransId(self.db)
        self.assertEqual(([], 1, last_trans_id),
                         (self.other_changes, new_gen, trans_id))
        self.assertEqual(10, self.st.get_sync_info(db2._replica_uid)[3])

    def test__set_trace_hook(self):
        called = []

        def cb(state):
            called.append(state)

        self.set_trace_hook(cb)
        self.st.sync_exchange([], 'replica', 0, None, self.receive_doc)
        self.st.record_sync_info('replica', 0, 'T-sid')
        self.assertEqual(['before whats_changed',
                          'after whats_changed',
                          'before get_docs',
                          'record_sync_info',
                          ],
                         called)

    def test__set_trace_hook_shallow(self):
        if (self.st._set_trace_hook_shallow == self.st._set_trace_hook
            or self.st._set_trace_hook_shallow.im_func ==
               SyncTarget._set_trace_hook_shallow.im_func):
            # shallow same as full
            expected = ['before whats_changed',
                        'after whats_changed',
                        'before get_docs',
                        'record_sync_info',
                        ]
        else:
            expected = ['sync_exchange', 'record_sync_info']

        called = []

        def cb(state):
            called.append(state)

        self.set_trace_hook(cb, shallow=True)
        self.st.sync_exchange([], 'replica', 0, None, self.receive_doc)
        self.st.record_sync_info('replica', 0, 'T-sid')
        self.assertEqual(expected, called)


def sync_via_synchronizer(test, db_source, db_target, trace_hook=None,
                          trace_hook_shallow=None):
    target = db_target.get_sync_target()
    trace_hook = trace_hook or trace_hook_shallow
    if trace_hook:
        target._set_trace_hook(trace_hook)
    return sync.Synchronizer(db_source, target).sync()


sync_scenarios = []
for name, scenario in tests.LOCAL_DATABASES_SCENARIOS:
    scenario = dict(scenario)
    scenario['do_sync'] = sync_via_synchronizer
    sync_scenarios.append((name, scenario))
    scenario = dict(scenario)


def make_database_for_http_test(test, replica_uid):
    if test.server is None:
        test.startServer()
    db = test.request_state._create_database(replica_uid)
    try:
        http_at = test._http_at
    except AttributeError:
        http_at = test._http_at = {}
    http_at[db] = replica_uid
    return db


def copy_database_for_http_test(test, db):
    # DO NOT COPY OR REUSE THIS CODE OUTSIDE TESTS: COPYING U1DB DATABASES IS
    # THE WRONG THING TO DO, THE ONLY REASON WE DO SO HERE IS TO TEST THAT WE
    # CORRECTLY DETECT IT HAPPENING SO THAT WE CAN RAISE ERRORS RATHER THAN
    # CORRUPT USER DATA. USE SYNC INSTEAD, OR WE WILL SEND NINJA TO YOUR HOUSE.
    if test.server is None:
        test.startServer()
    new_db = test.request_state._copy_database(db)
    try:
        http_at = test._http_at
    except AttributeError:
        http_at = test._http_at = {}
    path = db._replica_uid
    while path in http_at.values():
        path += 'copy'
    http_at[new_db] = path
    return new_db


def sync_via_synchronizer_and_http(test, db_source, db_target,
                                   trace_hook=None, trace_hook_shallow=None):
    if trace_hook:
        test.skipTest("full trace hook unsupported over http")
    path = test._http_at[db_target]
    target = http_target.HTTPSyncTarget.connect(test.getURL(path))
    if trace_hook_shallow:
        target._set_trace_hook_shallow(trace_hook_shallow)
    return sync.Synchronizer(db_source, target).sync()


sync_scenarios.append(('pyhttp', {
    'make_database_for_test': make_database_for_http_test,
    'copy_database_for_test': copy_database_for_http_test,
    'make_document_for_test': tests.make_document_for_test,
    'make_app_with_state': make_http_app,
    'do_sync': sync_via_synchronizer_and_http
    }))


class DatabaseSyncTests(tests.DatabaseBaseTests,
                        tests.TestCaseWithServer):

    scenarios = sync_scenarios
    do_sync = None                 # set by scenarios

    def create_database(self, replica_uid, sync_role=None):
        if replica_uid == 'test' and sync_role is None:
            # created up the chain by base class but unused
            return None
        db = self.create_database_for_role(replica_uid, sync_role)
        if sync_role:
            self._use_tracking[db] = (replica_uid, sync_role)
        return db

    def create_database_for_role(self, replica_uid, sync_role):
        # hook point for reuse
        return  super(DatabaseSyncTests, self).create_database(replica_uid)

    def copy_database(self, db, sync_role=None):
        # DO NOT COPY OR REUSE THIS CODE OUTSIDE TESTS: COPYING U1DB DATABASES
        # IS THE WRONG THING TO DO, THE ONLY REASON WE DO SO HERE IS TO TEST
        # THAT WE CORRECTLY DETECT IT HAPPENING SO THAT WE CAN RAISE ERRORS
        # RATHER THAN CORRUPT USER DATA. USE SYNC INSTEAD, OR WE WILL SEND
        # NINJA TO YOUR HOUSE.
        db_copy = super(DatabaseSyncTests, self).copy_database(db)
        name, orig_sync_role = self._use_tracking[db]
        self._use_tracking[db_copy] = (name + '(copy)', sync_role
                                       or orig_sync_role)
        return db_copy

    def sync(self, db_from, db_to, trace_hook=None,
             trace_hook_shallow=None):
        from_name, from_sync_role = self._use_tracking[db_from]
        to_name, to_sync_role = self._use_tracking[db_to]
        if from_sync_role not in ('source', 'both'):
            raise Exception("%s marked for %s use but used as source" %
                            (from_name, from_sync_role))
        if to_sync_role not in ('target', 'both'):
            raise Exception("%s marked for %s use but used as target" %
                            (to_name, to_sync_role))
        return self.do_sync(self, db_from, db_to, trace_hook,
                            trace_hook_shallow)

    def setUp(self):
        self._use_tracking = {}
        super(DatabaseSyncTests, self).setUp()

    def assertLastExchangeLog(self, db, expected):
        log = getattr(db, '_last_exchange_log', None)
        if log is None:
            return
        self.assertEqual(expected, log)

    def test_sync_tracks_db_generation_of_other(self):
        self.db1 = self.create_database('test1', 'source')
        self.db2 = self.create_database('test2', 'target')
        self.assertEqual(0, self.sync(self.db1, self.db2))
        self.assertEqual(
            (0, ''), self.db1._get_replica_gen_and_trans_id('test2'))
        self.assertEqual(
            (0, ''), self.db2._get_replica_gen_and_trans_id('test1'))
        self.assertLastExchangeLog(self.db2,
            {'receive': {'docs': [], 'last_known_gen': 0},
             'return': {'docs': [], 'last_gen': 0}})

    def test_sync_autoresolves(self):
        self.db1 = self.create_database('test1', 'source')
        self.db2 = self.create_database('test2', 'target')
        doc1 = self.db1.create_doc_from_json(simple_doc, doc_id='doc')
        rev1 = doc1.rev
        doc2 = self.db2.create_doc_from_json(simple_doc, doc_id='doc')
        rev2 = doc2.rev
        self.sync(self.db1, self.db2)
        doc = self.db1.get_doc('doc')
        self.assertFalse(doc.has_conflicts)
        self.assertEqual(doc.rev, self.db2.get_doc('doc').rev)
        v = vectorclock.VectorClockRev(doc.rev)
        self.assertTrue(v.is_newer(vectorclock.VectorClockRev(rev1)))
        self.assertTrue(v.is_newer(vectorclock.VectorClockRev(rev2)))

    def test_sync_autoresolves_moar(self):
        # here we test that when a database that has a conflicted document is
        # the source of a sync, and the target database has a revision of the
        # conflicted document that is newer than the source database's, and
        # that target's database's document's content is the same as the
        # source's document's conflict's, the source's document's conflict gets
        # autoresolved, and the source's document's revision bumped.
        #
        # idea is as follows:
        # A          B
        # a1         -
        #   `------->
        # a1         a1
        # v          v
        # a2         a1b1
        #   `------->
        # a1b1+a2    a1b1
        #            v
        # a1b1+a2    a1b2 (a1b2 has same content as a2)
        #   `------->
        # a3b2       a1b2 (autoresolved)
        #   `------->
        # a3b2       a3b2
        self.db1 = self.create_database('test1', 'source')
        self.db2 = self.create_database('test2', 'target')
        self.db1.create_doc_from_json(simple_doc, doc_id='doc')
        self.sync(self.db1, self.db2)
        for db, content in [(self.db1, '{}'), (self.db2, '{"hi": 42}')]:
            doc = db.get_doc('doc')
            doc.set_json(content)
            db.put_doc(doc)
        self.sync(self.db1, self.db2)
        # db1 and db2 now both have a doc of {hi:42}, but db1 has a conflict
        doc = self.db1.get_doc('doc')
        rev1 = doc.rev
        self.assertTrue(doc.has_conflicts)
        # set db2 to have a doc of {} (same as db1 before the conflict)
        doc = self.db2.get_doc('doc')
        doc.set_json('{}')
        self.db2.put_doc(doc)
        rev2 = doc.rev
        # sync it across
        self.sync(self.db1, self.db2)
        # tadaa!
        doc = self.db1.get_doc('doc')
        self.assertFalse(doc.has_conflicts)
        vec1 = vectorclock.VectorClockRev(rev1)
        vec2 = vectorclock.VectorClockRev(rev2)
        vec3 = vectorclock.VectorClockRev(doc.rev)
        self.assertTrue(vec3.is_newer(vec1))
        self.assertTrue(vec3.is_newer(vec2))
        # because the conflict is on the source, sync it another time
        self.sync(self.db1, self.db2)
        # make sure db2 now has the exact same thing
        self.assertEqual(self.db1.get_doc('doc'), self.db2.get_doc('doc'))

    def test_sync_autoresolves_moar_backwards(self):
        # here we test that when a database that has a conflicted document is
        # the target of a sync, and the source database has a revision of the
        # conflicted document that is newer than the target database's, and
        # that source's database's document's content is the same as the
        # target's document's conflict's, the target's document's conflict gets
        # autoresolved, and the document's revision bumped.
        #
        # idea is as follows:
        # A          B
        # a1         -
        #   `------->
        # a1         a1
        # v          v
        # a2         a1b1
        #   `------->
        # a1b1+a2    a1b1
        #            v
        # a1b1+a2    a1b2 (a1b2 has same content as a2)
        #   <-------'
        # a3b2       a3b2 (autoresolved and propagated)
        self.db1 = self.create_database('test1', 'both')
        self.db2 = self.create_database('test2', 'both')
        self.db1.create_doc_from_json(simple_doc, doc_id='doc')
        self.sync(self.db1, self.db2)
        for db, content in [(self.db1, '{}'), (self.db2, '{"hi": 42}')]:
            doc = db.get_doc('doc')
            doc.set_json(content)
            db.put_doc(doc)
        self.sync(self.db1, self.db2)
        # db1 and db2 now both have a doc of {hi:42}, but db1 has a conflict
        doc = self.db1.get_doc('doc')
        rev1 = doc.rev
        self.assertTrue(doc.has_conflicts)
        revc = self.db1.get_doc_conflicts('doc')[-1].rev
        # set db2 to have a doc of {} (same as db1 before the conflict)
        doc = self.db2.get_doc('doc')
        doc.set_json('{}')
        self.db2.put_doc(doc)
        rev2 = doc.rev
        # sync it across
        self.sync(self.db2, self.db1)
        # tadaa!
        doc = self.db1.get_doc('doc')
        self.assertFalse(doc.has_conflicts)
        vec1 = vectorclock.VectorClockRev(rev1)
        vec2 = vectorclock.VectorClockRev(rev2)
        vec3 = vectorclock.VectorClockRev(doc.rev)
        vecc = vectorclock.VectorClockRev(revc)
        self.assertTrue(vec3.is_newer(vec1))
        self.assertTrue(vec3.is_newer(vec2))
        self.assertTrue(vec3.is_newer(vecc))
        # make sure db2 now has the exact same thing
        self.assertEqual(self.db1.get_doc('doc'), self.db2.get_doc('doc'))

    def test_sync_autoresolves_moar_backwards_three(self):
        # same as autoresolves_moar_backwards, but with three databases (note
        # all the syncs go in the same direction -- this is a more natural
        # scenario):
        #
        # A          B          C
        # a1         -          -
        #   `------->
        # a1         a1         -
        #              `------->
        # a1         a1         a1
        # v          v
        # a2         a1b1       a1
        #  `------------------->
        # a2         a1b1       a2
        #              `------->
        #            a2+a1b1    a2
        #                       v
        # a2         a2+a1b1    a2c1 (same as a1b1)
        #  `------------------->
        # a2c1       a2+a1b1    a2c1
        #   `------->
        # a2b2c1     a2b2c1     a2c1
        self.db1 = self.create_database('test1', 'source')
        self.db2 = self.create_database('test2', 'both')
        self.db3 = self.create_database('test3', 'target')
        self.db1.create_doc_from_json(simple_doc, doc_id='doc')
        self.sync(self.db1, self.db2)
        self.sync(self.db2, self.db3)
        for db, content in [(self.db2, '{"hi": 42}'),
                            (self.db1, '{}'),
                            ]:
            doc = db.get_doc('doc')
            doc.set_json(content)
            db.put_doc(doc)
        self.sync(self.db1, self.db3)
        self.sync(self.db2, self.db3)
        # db2 and db3 now both have a doc of {}, but db2 has a
        # conflict
        doc = self.db2.get_doc('doc')
        self.assertTrue(doc.has_conflicts)
        revc = self.db2.get_doc_conflicts('doc')[-1].rev
        self.assertEqual('{}', doc.get_json())
        self.assertEqual(self.db3.get_doc('doc').get_json(), doc.get_json())
        self.assertEqual(self.db3.get_doc('doc').rev, doc.rev)
        # set db3 to have a doc of {hi:42} (same as db2 before the conflict)
        doc = self.db3.get_doc('doc')
        doc.set_json('{"hi": 42}')
        self.db3.put_doc(doc)
        rev3 = doc.rev
        # sync it across to db1
        self.sync(self.db1, self.db3)
        # db1 now has hi:42, with a rev that is newer than db2's doc
        doc = self.db1.get_doc('doc')
        rev1 = doc.rev
        self.assertFalse(doc.has_conflicts)
        self.assertEqual('{"hi": 42}', doc.get_json())
        VCR = vectorclock.VectorClockRev
        self.assertTrue(VCR(rev1).is_newer(VCR(self.db2.get_doc('doc').rev)))
        # so sync it to db2
        self.sync(self.db1, self.db2)
        # tadaa!
        doc = self.db2.get_doc('doc')
        self.assertFalse(doc.has_conflicts)
        # db2's revision of the document is strictly newer than db1's before
        # the sync, and db3's before that sync way back when
        self.assertTrue(VCR(doc.rev).is_newer(VCR(rev1)))
        self.assertTrue(VCR(doc.rev).is_newer(VCR(rev3)))
        self.assertTrue(VCR(doc.rev).is_newer(VCR(revc)))
        # make sure both dbs now have the exact same thing
        self.assertEqual(self.db1.get_doc('doc'), self.db2.get_doc('doc'))

    def test_sync_puts_changes(self):
        self.db1 = self.create_database('test1', 'source')
        self.db2 = self.create_database('test2', 'target')
        doc = self.db1.create_doc_from_json(simple_doc)
        self.assertEqual(1, self.sync(self.db1, self.db2))
        self.assertGetDoc(self.db2, doc.doc_id, doc.rev, simple_doc, False)
        self.assertEqual(1, self.db1._get_replica_gen_and_trans_id('test2')[0])
        self.assertEqual(1, self.db2._get_replica_gen_and_trans_id('test1')[0])
        self.assertLastExchangeLog(self.db2,
            {'receive': {'docs': [(doc.doc_id, doc.rev)],
                         'source_uid': 'test1',
                         'source_gen': 1, 'last_known_gen': 0},
             'return': {'docs': [], 'last_gen': 1}})

    def test_sync_pulls_changes(self):
        self.db1 = self.create_database('test1', 'source')
        self.db2 = self.create_database('test2', 'target')
        doc = self.db2.create_doc_from_json(simple_doc)
        self.db1.create_index('test-idx', 'key')
        self.assertEqual(0, self.sync(self.db1, self.db2))
        self.assertGetDoc(self.db1, doc.doc_id, doc.rev, simple_doc, False)
        self.assertEqual(1, self.db1._get_replica_gen_and_trans_id('test2')[0])
        self.assertEqual(1, self.db2._get_replica_gen_and_trans_id('test1')[0])
        self.assertLastExchangeLog(self.db2,
            {'receive': {'docs': [], 'last_known_gen': 0},
             'return': {'docs': [(doc.doc_id, doc.rev)],
                        'last_gen': 1}})
        self.assertEqual([doc], self.db1.get_from_index('test-idx', 'value'))

    def test_sync_pulling_doesnt_update_other_if_changed(self):
        self.db1 = self.create_database('test1', 'source')
        self.db2 = self.create_database('test2', 'target')
        doc = self.db2.create_doc_from_json(simple_doc)
        # After the local side has sent its list of docs, before we start
        # receiving the "targets" response, we update the local database with a
        # new record.
        # When we finish synchronizing, we can notice that something locally
        # was updated, and we cannot tell c2 our new updated generation

        def before_get_docs(state):
            if state != 'before get_docs':
                return
            self.db1.create_doc_from_json(simple_doc)

        self.assertEqual(0, self.sync(self.db1, self.db2,
                                      trace_hook=before_get_docs))
        self.assertLastExchangeLog(self.db2,
            {'receive': {'docs': [], 'last_known_gen': 0},
             'return': {'docs': [(doc.doc_id, doc.rev)],
                        'last_gen': 1}})
        self.assertEqual(1, self.db1._get_replica_gen_and_trans_id('test2')[0])
        # c2 should not have gotten a '_record_sync_info' call, because the
        # local database had been updated more than just by the messages
        # returned from c2.
        self.assertEqual(
            (0, ''), self.db2._get_replica_gen_and_trans_id('test1'))

    def test_sync_doesnt_update_other_if_nothing_pulled(self):
        self.db1 = self.create_database('test1', 'source')
        self.db2 = self.create_database('test2', 'target')
        self.db1.create_doc_from_json(simple_doc)

        def no_record_sync_info(state):
            if state != 'record_sync_info':
                return
            self.fail('SyncTarget.record_sync_info was called')
        self.assertEqual(1, self.sync(self.db1, self.db2,
                                      trace_hook_shallow=no_record_sync_info))
        self.assertEqual(
            1,
            self.db2._get_replica_gen_and_trans_id(self.db1._replica_uid)[0])

    def test_sync_ignores_convergence(self):
        self.db1 = self.create_database('test1', 'source')
        self.db2 = self.create_database('test2', 'both')
        doc = self.db1.create_doc_from_json(simple_doc)
        self.db3 = self.create_database('test3', 'target')
        self.assertEqual(1, self.sync(self.db1, self.db3))
        self.assertEqual(0, self.sync(self.db2, self.db3))
        self.assertEqual(1, self.sync(self.db1, self.db2))
        self.assertLastExchangeLog(self.db2,
            {'receive': {'docs': [(doc.doc_id, doc.rev)],
                         'source_uid': 'test1',
                         'source_gen': 1, 'last_known_gen': 0},
             'return': {'docs': [], 'last_gen': 1}})

    def test_sync_ignores_superseded(self):
        self.db1 = self.create_database('test1', 'both')
        self.db2 = self.create_database('test2', 'both')
        doc = self.db1.create_doc_from_json(simple_doc)
        doc_rev1 = doc.rev
        self.db3 = self.create_database('test3', 'target')
        self.sync(self.db1, self.db3)
        self.sync(self.db2, self.db3)
        new_content = '{"key": "altval"}'
        doc.set_json(new_content)
        self.db1.put_doc(doc)
        doc_rev2 = doc.rev
        self.sync(self.db2, self.db1)
        self.assertLastExchangeLog(self.db1,
            {'receive': {'docs': [(doc.doc_id, doc_rev1)],
                         'source_uid': 'test2',
                         'source_gen': 1, 'last_known_gen': 0},
             'return': {'docs': [(doc.doc_id, doc_rev2)],
                        'last_gen': 2}})
        self.assertGetDoc(self.db1, doc.doc_id, doc_rev2, new_content, False)

    def test_sync_sees_remote_conflicted(self):
        self.db1 = self.create_database('test1', 'source')
        self.db2 = self.create_database('test2', 'target')
        doc1 = self.db1.create_doc_from_json(simple_doc)
        doc_id = doc1.doc_id
        doc1_rev = doc1.rev
        self.db1.create_index('test-idx', 'key')
        new_doc = '{"key": "altval"}'
        doc2 = self.db2.create_doc_from_json(new_doc, doc_id=doc_id)
        doc2_rev = doc2.rev
        self.assertTransactionLog([doc1.doc_id], self.db1)
        self.sync(self.db1, self.db2)
        self.assertLastExchangeLog(self.db2,
            {'receive': {'docs': [(doc_id, doc1_rev)],
                         'source_uid': 'test1',
                         'source_gen': 1, 'last_known_gen': 0},
             'return': {'docs': [(doc_id, doc2_rev)],
                        'last_gen': 1}})
        self.assertTransactionLog([doc_id, doc_id], self.db1)
        self.assertGetDoc(self.db1, doc_id, doc2_rev, new_doc, True)
        self.assertGetDoc(self.db2, doc_id, doc2_rev, new_doc, False)
        from_idx = self.db1.get_from_index('test-idx', 'altval')[0]
        self.assertEqual(doc2.doc_id, from_idx.doc_id)
        self.assertEqual(doc2.rev, from_idx.rev)
        self.assertTrue(from_idx.has_conflicts)
        self.assertEqual([], self.db1.get_from_index('test-idx', 'value'))

    def test_sync_sees_remote_delete_conflicted(self):
        self.db1 = self.create_database('test1', 'source')
        self.db2 = self.create_database('test2', 'target')
        doc1 = self.db1.create_doc_from_json(simple_doc)
        doc_id = doc1.doc_id
        self.db1.create_index('test-idx', 'key')
        self.sync(self.db1, self.db2)
        doc2 = self.make_document(doc1.doc_id, doc1.rev, doc1.get_json())
        new_doc = '{"key": "altval"}'
        doc1.set_json(new_doc)
        self.db1.put_doc(doc1)
        self.db2.delete_doc(doc2)
        self.assertTransactionLog([doc_id, doc_id], self.db1)
        self.sync(self.db1, self.db2)
        self.assertLastExchangeLog(self.db2,
            {'receive': {'docs': [(doc_id, doc1.rev)],
                         'source_uid': 'test1',
                         'source_gen': 2, 'last_known_gen': 1},
             'return': {'docs': [(doc_id, doc2.rev)],
                        'last_gen': 2}})
        self.assertTransactionLog([doc_id, doc_id, doc_id], self.db1)
        self.assertGetDocIncludeDeleted(self.db1, doc_id, doc2.rev, None, True)
        self.assertGetDocIncludeDeleted(
            self.db2, doc_id, doc2.rev, None, False)
        self.assertEqual([], self.db1.get_from_index('test-idx', 'value'))

    def test_sync_local_race_conflicted(self):
        self.db1 = self.create_database('test1', 'source')
        self.db2 = self.create_database('test2', 'target')
        doc = self.db1.create_doc_from_json(simple_doc)
        doc_id = doc.doc_id
        doc1_rev = doc.rev
        self.db1.create_index('test-idx', 'key')
        self.sync(self.db1, self.db2)
        content1 = '{"key": "localval"}'
        content2 = '{"key": "altval"}'
        doc.set_json(content2)
        self.db2.put_doc(doc)
        doc2_rev2 = doc.rev
        triggered = []

        def after_whatschanged(state):
            if state != 'after whats_changed':
                return
            triggered.append(True)
            doc = self.make_document(doc_id, doc1_rev, content1)
            self.db1.put_doc(doc)

        self.sync(self.db1, self.db2, trace_hook=after_whatschanged)
        self.assertEqual([True], triggered)
        self.assertGetDoc(self.db1, doc_id, doc2_rev2, content2, True)
        from_idx = self.db1.get_from_index('test-idx', 'altval')[0]
        self.assertEqual(doc.doc_id, from_idx.doc_id)
        self.assertEqual(doc.rev, from_idx.rev)
        self.assertTrue(from_idx.has_conflicts)
        self.assertEqual([], self.db1.get_from_index('test-idx', 'value'))
        self.assertEqual([], self.db1.get_from_index('test-idx', 'localval'))

    def test_sync_propagates_deletes(self):
        self.db1 = self.create_database('test1', 'source')
        self.db2 = self.create_database('test2', 'both')
        doc1 = self.db1.create_doc_from_json(simple_doc)
        doc_id = doc1.doc_id
        self.db1.create_index('test-idx', 'key')
        self.sync(self.db1, self.db2)
        self.db2.create_index('test-idx', 'key')
        self.db3 = self.create_database('test3', 'target')
        self.sync(self.db1, self.db3)
        self.db1.delete_doc(doc1)
        deleted_rev = doc1.rev
        self.sync(self.db1, self.db2)
        self.assertLastExchangeLog(self.db2,
            {'receive': {'docs': [(doc_id, deleted_rev)],
                         'source_uid': 'test1',
                         'source_gen': 2, 'last_known_gen': 1},
             'return': {'docs': [], 'last_gen': 2}})
        self.assertGetDocIncludeDeleted(
            self.db1, doc_id, deleted_rev, None, False)
        self.assertGetDocIncludeDeleted(
            self.db2, doc_id, deleted_rev, None, False)
        self.assertEqual([], self.db1.get_from_index('test-idx', 'value'))
        self.assertEqual([], self.db2.get_from_index('test-idx', 'value'))
        self.sync(self.db2, self.db3)
        self.assertLastExchangeLog(self.db3,
            {'receive': {'docs': [(doc_id, deleted_rev)],
                         'source_uid': 'test2',
                         'source_gen': 2, 'last_known_gen': 0},
             'return': {'docs': [], 'last_gen': 2}})
        self.assertGetDocIncludeDeleted(
            self.db3, doc_id, deleted_rev, None, False)

    def test_sync_propagates_resolution(self):
        self.db1 = self.create_database('test1', 'both')
        self.db2 = self.create_database('test2', 'both')
        doc1 = self.db1.create_doc_from_json('{"a": 1}', doc_id='the-doc')
        db3 = self.create_database('test3', 'both')
        self.sync(self.db2, self.db1)
        self.assertEqual(
            self.db1._get_generation_info(),
            self.db2._get_replica_gen_and_trans_id(self.db1._replica_uid))
        self.assertEqual(
            self.db2._get_generation_info(),
            self.db1._get_replica_gen_and_trans_id(self.db2._replica_uid))
        self.sync(db3, self.db1)
        # update on 2
        doc2 = self.make_document('the-doc', doc1.rev, '{"a": 2}')
        self.db2.put_doc(doc2)
        self.sync(self.db2, db3)
        self.assertEqual(db3.get_doc('the-doc').rev, doc2.rev)
        # update on 1
        doc1.set_json('{"a": 3}')
        self.db1.put_doc(doc1)
        # conflicts
        self.sync(self.db2, self.db1)
        self.sync(db3, self.db1)
        self.assertTrue(self.db2.get_doc('the-doc').has_conflicts)
        self.assertTrue(db3.get_doc('the-doc').has_conflicts)
        # resolve
        conflicts = self.db2.get_doc_conflicts('the-doc')
        doc4 = self.make_document('the-doc', None, '{"a": 4}')
        revs = [doc.rev for doc in conflicts]
        self.db2.resolve_doc(doc4, revs)
        doc2 = self.db2.get_doc('the-doc')
        self.assertEqual(doc4.get_json(), doc2.get_json())
        self.assertFalse(doc2.has_conflicts)
        self.sync(self.db2, db3)
        doc3 = db3.get_doc('the-doc')
        self.assertEqual(doc4.get_json(), doc3.get_json())
        self.assertFalse(doc3.has_conflicts)

    def test_sync_supersedes_conflicts(self):
        self.db1 = self.create_database('test1', 'both')
        self.db2 = self.create_database('test2', 'target')
        db3 = self.create_database('test3', 'both')
        doc1 = self.db1.create_doc_from_json('{"a": 1}', doc_id='the-doc')
        self.db2.create_doc_from_json('{"b": 1}', doc_id='the-doc')
        db3.create_doc_from_json('{"c": 1}', doc_id='the-doc')
        self.sync(db3, self.db1)
        self.assertEqual(
            self.db1._get_generation_info(),
            db3._get_replica_gen_and_trans_id(self.db1._replica_uid))
        self.assertEqual(
            db3._get_generation_info(),
            self.db1._get_replica_gen_and_trans_id(db3._replica_uid))
        self.sync(db3, self.db2)
        self.assertEqual(
            self.db2._get_generation_info(),
            db3._get_replica_gen_and_trans_id(self.db2._replica_uid))
        self.assertEqual(
            db3._get_generation_info(),
            self.db2._get_replica_gen_and_trans_id(db3._replica_uid))
        self.assertEqual(3, len(db3.get_doc_conflicts('the-doc')))
        doc1.set_json('{"a": 2}')
        self.db1.put_doc(doc1)
        self.sync(db3, self.db1)
        # original doc1 should have been removed from conflicts
        self.assertEqual(3, len(db3.get_doc_conflicts('the-doc')))

    def test_sync_stops_after_get_sync_info(self):
        self.db1 = self.create_database('test1', 'source')
        self.db2 = self.create_database('test2', 'target')
        self.db1.create_doc_from_json(tests.simple_doc)
        self.sync(self.db1, self.db2)

        def put_hook(state):
            self.fail("Tracehook triggered for %s" % (state,))

        self.sync(self.db1, self.db2, trace_hook_shallow=put_hook)

    def test_sync_detects_rollback_in_source(self):
        self.db1 = self.create_database('test1', 'source')
        self.db2 = self.create_database('test2', 'target')
        self.db1.create_doc_from_json(tests.simple_doc, doc_id='doc1')
        self.sync(self.db1, self.db2)
        db1_copy = self.copy_database(self.db1)
        self.db1.create_doc_from_json(tests.simple_doc, doc_id='doc2')
        self.sync(self.db1, self.db2)
        self.assertRaises(
            errors.InvalidGeneration, self.sync, db1_copy, self.db2)

    def test_sync_detects_rollback_in_target(self):
        self.db1 = self.create_database('test1', 'source')
        self.db2 = self.create_database('test2', 'target')
        self.db1.create_doc_from_json(tests.simple_doc, doc_id="divergent")
        self.sync(self.db1, self.db2)
        db2_copy = self.copy_database(self.db2)
        self.db2.create_doc_from_json(tests.simple_doc, doc_id='doc2')
        self.sync(self.db1, self.db2)
        self.assertRaises(
            errors.InvalidGeneration, self.sync, self.db1, db2_copy)

    def test_sync_detects_diverged_source(self):
        self.db1 = self.create_database('test1', 'source')
        self.db2 = self.create_database('test2', 'target')
        db3 = self.copy_database(self.db1)
        self.db1.create_doc_from_json(tests.simple_doc, doc_id="divergent")
        db3.create_doc_from_json(tests.simple_doc, doc_id="divergent")
        self.sync(self.db1, self.db2)
        self.assertRaises(
            errors.InvalidTransactionId, self.sync, db3, self.db2)

    def test_sync_detects_diverged_target(self):
        self.db1 = self.create_database('test1', 'source')
        self.db2 = self.create_database('test2', 'target')
        db3 = self.copy_database(self.db2)
        db3.create_doc_from_json(tests.nested_doc, doc_id="divergent")
        self.db1.create_doc_from_json(tests.simple_doc, doc_id="divergent")
        self.sync(self.db1, self.db2)
        self.assertRaises(
            errors.InvalidTransactionId, self.sync, self.db1, db3)

    def test_sync_detects_rollback_and_divergence_in_source(self):
        self.db1 = self.create_database('test1', 'source')
        self.db2 = self.create_database('test2', 'target')
        self.db1.create_doc_from_json(tests.simple_doc, doc_id='doc1')
        self.sync(self.db1, self.db2)
        db1_copy = self.copy_database(self.db1)
        self.db1.create_doc_from_json(tests.simple_doc, doc_id='doc2')
        self.db1.create_doc_from_json(tests.simple_doc, doc_id='doc3')
        self.sync(self.db1, self.db2)
        db1_copy.create_doc_from_json(tests.simple_doc, doc_id='doc2')
        db1_copy.create_doc_from_json(tests.simple_doc, doc_id='doc3')
        self.assertRaises(
            errors.InvalidTransactionId, self.sync, db1_copy, self.db2)

    def test_sync_detects_rollback_and_divergence_in_target(self):
        self.db1 = self.create_database('test1', 'source')
        self.db2 = self.create_database('test2', 'target')
        self.db1.create_doc_from_json(tests.simple_doc, doc_id="divergent")
        self.sync(self.db1, self.db2)
        db2_copy = self.copy_database(self.db2)
        self.db2.create_doc_from_json(tests.simple_doc, doc_id='doc2')
        self.db2.create_doc_from_json(tests.simple_doc, doc_id='doc3')
        self.sync(self.db1, self.db2)
        db2_copy.create_doc_from_json(tests.simple_doc, doc_id='doc2')
        db2_copy.create_doc_from_json(tests.simple_doc, doc_id='doc3')
        self.assertRaises(
            errors.InvalidTransactionId, self.sync, self.db1, db2_copy)


class TestDbSync(tests.TestCaseWithServer):
    """Test db.sync remote sync shortcut"""

    scenarios = [
        ('py-http', {
            'make_app_with_state': make_http_app,
            'make_database_for_test': tests.make_memory_database_for_test,
            }),
        ('py-oauth-http', {
            'make_app_with_state': make_oauth_http_app,
            'make_database_for_test': tests.make_memory_database_for_test,
            'oauth': True
            }),
        ]

    oauth = False

    def do_sync(self, target_name):
        if self.oauth:
            path = '~/' + target_name
            extra = dict(creds={'oauth': {
                'consumer_key': tests.consumer1.key,
                'consumer_secret': tests.consumer1.secret,
                'token_key': tests.token1.key,
                'token_secret': tests.token1.secret
                }})
        else:
            path = target_name
            extra = {}
        target_url = self.getURL(path)
        return self.db.sync(target_url, **extra)

    def setUp(self):
        super(TestDbSync, self).setUp()
        self.startServer()
        self.db = self.make_database_for_test(self, 'test1')
        self.db2 = self.request_state._create_database('test2.db')

    def test_db_sync(self):
        doc1 = self.db.create_doc_from_json(tests.simple_doc)
        doc2 = self.db2.create_doc_from_json(tests.nested_doc)
        local_gen_before_sync = self.do_sync('test2.db')
        gen, _, changes = self.db.whats_changed(local_gen_before_sync)
        self.assertEqual(1, len(changes))
        self.assertEqual(doc2.doc_id, changes[0][0])
        self.assertEqual(1, gen - local_gen_before_sync)
        self.assertGetDoc(self.db2, doc1.doc_id, doc1.rev, tests.simple_doc,
                          False)
        self.assertGetDoc(self.db, doc2.doc_id, doc2.rev, tests.nested_doc,
                          False)

    def test_db_sync_autocreate(self):
        doc1 = self.db.create_doc_from_json(tests.simple_doc)
        local_gen_before_sync = self.do_sync('test3.db')
        gen, _, changes = self.db.whats_changed(local_gen_before_sync)
        self.assertEqual(0, gen - local_gen_before_sync)
        db3 = self.request_state.open_database('test3.db')
        gen, _, changes = db3.whats_changed()
        self.assertEqual(1, len(changes))
        self.assertEqual(doc1.doc_id, changes[0][0])
        self.assertGetDoc(db3, doc1.doc_id, doc1.rev, tests.simple_doc,
                          False)
        t_gen, _ = self.db._get_replica_gen_and_trans_id('test3.db')
        s_gen, _ = db3._get_replica_gen_and_trans_id('test1')
        self.assertEqual(1, t_gen)
        self.assertEqual(1, s_gen)


class TestRemoteSyncIntegration(tests.TestCaseWithServer):
    """Integration tests for the most common sync scenario local -> remote"""

    make_app_with_state = staticmethod(make_http_app)

    def setUp(self):
        super(TestRemoteSyncIntegration, self).setUp()
        self.startServer()
        self.db1 = inmemory.InMemoryDatabase('test1')
        self.db2 = self.request_state._create_database('test2')

    def test_sync_tracks_generations_incrementally(self):
        doc11 = self.db1.create_doc_from_json('{"a": 1}')
        doc12 = self.db1.create_doc_from_json('{"a": 2}')
        doc21 = self.db2.create_doc_from_json('{"b": 1}')
        doc22 = self.db2.create_doc_from_json('{"b": 2}')
        #sanity
        self.assertEqual(2, len(self.db1._get_transaction_log()))
        self.assertEqual(2, len(self.db2._get_transaction_log()))
        progress1 = []
        progress2 = []
        _do_set_replica_gen_and_trans_id = \
            self.db1._do_set_replica_gen_and_trans_id

        def set_sync_generation_witness1(other_uid, other_gen, trans_id):
            progress1.append((other_uid, other_gen,
                [d for d, t in self.db1._get_transaction_log()[2:]]))
            _do_set_replica_gen_and_trans_id(other_uid, other_gen, trans_id)
        self.patch(self.db1, '_do_set_replica_gen_and_trans_id',
                   set_sync_generation_witness1)
        _do_set_replica_gen_and_trans_id2 = \
            self.db2._do_set_replica_gen_and_trans_id

        def set_sync_generation_witness2(other_uid, other_gen, trans_id):
            progress2.append((other_uid, other_gen,
                [d for d, t in self.db2._get_transaction_log()[2:]]))
            _do_set_replica_gen_and_trans_id2(other_uid, other_gen, trans_id)
        self.patch(self.db2, '_do_set_replica_gen_and_trans_id',
                   set_sync_generation_witness2)

        db2_url = self.getURL('test2')
        self.db1.sync(db2_url)

        self.assertEqual([('test2', 1, [doc21.doc_id]),
                          ('test2', 2, [doc21.doc_id, doc22.doc_id]),
                          ('test2', 4, [doc21.doc_id, doc22.doc_id])],
                         progress1)
        self.assertEqual([('test1', 1, [doc11.doc_id]),
                          ('test1', 2, [doc11.doc_id, doc12.doc_id]),
                          ('test1', 4, [doc11.doc_id, doc12.doc_id])],
                         progress2)


load_tests = tests.load_with_scenarios
