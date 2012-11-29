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

import cStringIO
import os
import sys
try:
    import simplejson as json
except ImportError:
    import json  # noqa
import subprocess

from u1db import (
    errors,
    open as u1db_open,
    tests,
    vectorclock,
    )
from u1db.commandline import (
    client,
    serve,
    )
from u1db.tests.commandline import safe_close
from u1db.tests import test_remote_sync_target


class TestArgs(tests.TestCase):
    """These tests are meant to test just the argument parsing.

    Each Command should have at least one test, possibly more if it allows
    optional arguments, etc.
    """

    def setUp(self):
        super(TestArgs, self).setUp()
        self.parser = client.client_commands.make_argparser()

    def parse_args(self, args):
        # ArgumentParser.parse_args doesn't play very nicely with a test suite,
        # so we trap SystemExit in case something is wrong with the args we're
        # parsing.
        try:
            return self.parser.parse_args(args)
        except SystemExit:
            raise AssertionError('got SystemExit')

    def test_create(self):
        args = self.parse_args(['create', 'test.db'])
        self.assertEqual(client.CmdCreate, args.subcommand)
        self.assertEqual('test.db', args.database)
        self.assertEqual(None, args.doc_id)
        self.assertEqual(None, args.infile)

    def test_create_custom_doc_id(self):
        args = self.parse_args(['create', '--id', 'xyz', 'test.db'])
        self.assertEqual(client.CmdCreate, args.subcommand)
        self.assertEqual('test.db', args.database)
        self.assertEqual('xyz', args.doc_id)
        self.assertEqual(None, args.infile)

    def test_delete(self):
        args = self.parse_args(['delete', 'test.db', 'doc-id', 'doc-rev'])
        self.assertEqual(client.CmdDelete, args.subcommand)
        self.assertEqual('test.db', args.database)
        self.assertEqual('doc-id', args.doc_id)
        self.assertEqual('doc-rev', args.doc_rev)

    def test_get(self):
        args = self.parse_args(['get', 'test.db', 'doc-id'])
        self.assertEqual(client.CmdGet, args.subcommand)
        self.assertEqual('test.db', args.database)
        self.assertEqual('doc-id', args.doc_id)
        self.assertEqual(None, args.outfile)

    def test_get_dash(self):
        args = self.parse_args(['get', 'test.db', 'doc-id', '-'])
        self.assertEqual(client.CmdGet, args.subcommand)
        self.assertEqual('test.db', args.database)
        self.assertEqual('doc-id', args.doc_id)
        self.assertEqual(sys.stdout, args.outfile)

    def test_init_db(self):
        args = self.parse_args(
            ['init-db', 'test.db', '--replica-uid=replica-uid'])
        self.assertEqual(client.CmdInitDB, args.subcommand)
        self.assertEqual('test.db', args.database)
        self.assertEqual('replica-uid', args.replica_uid)

    def test_init_db_no_replica(self):
        args = self.parse_args(['init-db', 'test.db'])
        self.assertEqual(client.CmdInitDB, args.subcommand)
        self.assertEqual('test.db', args.database)
        self.assertIs(None, args.replica_uid)

    def test_put(self):
        args = self.parse_args(['put', 'test.db', 'doc-id', 'old-doc-rev'])
        self.assertEqual(client.CmdPut, args.subcommand)
        self.assertEqual('test.db', args.database)
        self.assertEqual('doc-id', args.doc_id)
        self.assertEqual('old-doc-rev', args.doc_rev)
        self.assertEqual(None, args.infile)

    def test_sync(self):
        args = self.parse_args(['sync', 'source', 'target'])
        self.assertEqual(client.CmdSync, args.subcommand)
        self.assertEqual('source', args.source)
        self.assertEqual('target', args.target)

    def test_create_index(self):
        args = self.parse_args(['create-index', 'db', 'index', 'expression'])
        self.assertEqual(client.CmdCreateIndex, args.subcommand)
        self.assertEqual('db', args.database)
        self.assertEqual('index', args.index)
        self.assertEqual(['expression'], args.expression)

    def test_create_index_multi_expression(self):
        args = self.parse_args(['create-index', 'db', 'index', 'e1', 'e2'])
        self.assertEqual(client.CmdCreateIndex, args.subcommand)
        self.assertEqual('db', args.database)
        self.assertEqual('index', args.index)
        self.assertEqual(['e1', 'e2'], args.expression)

    def test_list_indexes(self):
        args = self.parse_args(['list-indexes', 'db'])
        self.assertEqual(client.CmdListIndexes, args.subcommand)
        self.assertEqual('db', args.database)

    def test_delete_index(self):
        args = self.parse_args(['delete-index', 'db', 'index'])
        self.assertEqual(client.CmdDeleteIndex, args.subcommand)
        self.assertEqual('db', args.database)
        self.assertEqual('index', args.index)

    def test_get_index_keys(self):
        args = self.parse_args(['get-index-keys', 'db', 'index'])
        self.assertEqual(client.CmdGetIndexKeys, args.subcommand)
        self.assertEqual('db', args.database)
        self.assertEqual('index', args.index)

    def test_get_from_index(self):
        args = self.parse_args(['get-from-index', 'db', 'index', 'foo'])
        self.assertEqual(client.CmdGetFromIndex, args.subcommand)
        self.assertEqual('db', args.database)
        self.assertEqual('index', args.index)
        self.assertEqual(['foo'], args.values)

    def test_get_doc_conflicts(self):
        args = self.parse_args(['get-doc-conflicts', 'db', 'doc-id'])
        self.assertEqual(client.CmdGetDocConflicts, args.subcommand)
        self.assertEqual('db', args.database)
        self.assertEqual('doc-id', args.doc_id)

    def test_resolve(self):
        args = self.parse_args(
            ['resolve-doc', 'db', 'doc-id', 'rev:1', 'other:1'])
        self.assertEqual(client.CmdResolve, args.subcommand)
        self.assertEqual('db', args.database)
        self.assertEqual('doc-id', args.doc_id)
        self.assertEqual(['rev:1', 'other:1'], args.doc_revs)
        self.assertEqual(None, args.infile)


class TestCaseWithDB(tests.TestCase):
    """These next tests are meant to have one class per Command.

    It is meant to test the inner workings of each command. The detailed
    testing should happen in these classes. Stuff like how it handles errors,
    etc. should be done here.
    """

    def setUp(self):
        super(TestCaseWithDB, self).setUp()
        self.working_dir = self.createTempDir()
        self.db_path = self.working_dir + '/test.db'
        self.db = u1db_open(self.db_path, create=True)
        self.db._set_replica_uid('test')
        self.addCleanup(self.db.close)

    def make_command(self, cls, stdin_content=''):
        inf = cStringIO.StringIO(stdin_content)
        out = cStringIO.StringIO()
        err = cStringIO.StringIO()
        return cls(inf, out, err)


class TestCmdCreate(TestCaseWithDB):

    def test_create(self):
        cmd = self.make_command(client.CmdCreate)
        inf = cStringIO.StringIO(tests.simple_doc)
        cmd.run(self.db_path, inf, 'test-id')
        doc = self.db.get_doc('test-id')
        self.assertEqual(tests.simple_doc, doc.get_json())
        self.assertFalse(doc.has_conflicts)
        self.assertEqual('', cmd.stdout.getvalue())
        self.assertEqual('id: test-id\nrev: %s\n' % (doc.rev,),
                         cmd.stderr.getvalue())


class TestCmdDelete(TestCaseWithDB):

    def test_delete(self):
        doc = self.db.create_doc_from_json(tests.simple_doc)
        cmd = self.make_command(client.CmdDelete)
        cmd.run(self.db_path, doc.doc_id, doc.rev)
        doc2 = self.db.get_doc(doc.doc_id, include_deleted=True)
        self.assertEqual(doc.doc_id, doc2.doc_id)
        self.assertNotEqual(doc.rev, doc2.rev)
        self.assertIs(None, doc2.get_json())
        self.assertEqual('', cmd.stdout.getvalue())
        self.assertEqual('rev: %s\n' % (doc2.rev,), cmd.stderr.getvalue())

    def test_delete_fails_if_nonexistent(self):
        doc = self.db.create_doc_from_json(tests.simple_doc)
        db2_path = self.db_path + '.typo'
        cmd = self.make_command(client.CmdDelete)
        # TODO: We should really not be showing a traceback here. But we need
        #       to teach the commandline infrastructure how to handle
        #       exceptions.
        #       However, we *do* want to test that the db doesn't get created
        #       by accident.
        self.assertRaises(errors.DatabaseDoesNotExist,
            cmd.run, db2_path, doc.doc_id, doc.rev)
        self.assertFalse(os.path.exists(db2_path))

    def test_delete_no_such_doc(self):
        cmd = self.make_command(client.CmdDelete)
        # TODO: We should really not be showing a traceback here. But we need
        #       to teach the commandline infrastructure how to handle
        #       exceptions.
        self.assertRaises(errors.DocumentDoesNotExist,
            cmd.run, self.db_path, 'no-doc-id', 'no-rev')

    def test_delete_bad_rev(self):
        doc = self.db.create_doc_from_json(tests.simple_doc)
        cmd = self.make_command(client.CmdDelete)
        self.assertRaises(errors.RevisionConflict,
            cmd.run, self.db_path, doc.doc_id, 'not-the-actual-doc-rev:1')
        # TODO: Test that we get a pretty output.


class TestCmdGet(TestCaseWithDB):

    def setUp(self):
        super(TestCmdGet, self).setUp()
        self.doc = self.db.create_doc_from_json(
            tests.simple_doc, doc_id='my-test-doc')

    def test_get_simple(self):
        cmd = self.make_command(client.CmdGet)
        cmd.run(self.db_path, 'my-test-doc', None)
        self.assertEqual(tests.simple_doc + "\n", cmd.stdout.getvalue())
        self.assertEqual('rev: %s\n' % (self.doc.rev,),
                         cmd.stderr.getvalue())

    def test_get_conflict(self):
        doc = self.make_document('my-test-doc', 'other:1', '{}', False)
        self.db._put_doc_if_newer(
            doc, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        cmd = self.make_command(client.CmdGet)
        cmd.run(self.db_path, 'my-test-doc', None)
        self.assertEqual('{}\n', cmd.stdout.getvalue())
        self.assertEqual('rev: %s\nDocument has conflicts.\n' % (doc.rev,),
                         cmd.stderr.getvalue())

    def test_get_fail(self):
        cmd = self.make_command(client.CmdGet)
        result = cmd.run(self.db_path, 'doc-not-there', None)
        self.assertEqual(1, result)
        self.assertEqual("", cmd.stdout.getvalue())
        self.assertTrue("not found" in cmd.stderr.getvalue())

    def test_get_no_database(self):
        cmd = self.make_command(client.CmdGet)
        retval = cmd.run(self.db_path + "__DOES_NOT_EXIST", "my-doc", None)
        self.assertEqual(retval, 1)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual(cmd.stderr.getvalue(), 'Database does not exist.\n')


class TestCmdGetDocConflicts(TestCaseWithDB):

    def setUp(self):
        super(TestCmdGetDocConflicts, self).setUp()
        self.doc1 = self.db.create_doc_from_json(
            tests.simple_doc, doc_id='my-doc')
        self.doc2 = self.make_document('my-doc', 'other:1', '{}', False)
        self.db._put_doc_if_newer(
            self.doc2, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')

    def test_get_doc_conflicts_none(self):
        self.db.create_doc_from_json(tests.simple_doc, doc_id='a-doc')
        cmd = self.make_command(client.CmdGetDocConflicts)
        cmd.run(self.db_path, 'a-doc')
        self.assertEqual([], json.loads(cmd.stdout.getvalue()))
        self.assertEqual('', cmd.stderr.getvalue())

    def test_get_doc_conflicts_simple(self):
        cmd = self.make_command(client.CmdGetDocConflicts)
        cmd.run(self.db_path, 'my-doc')
        self.assertEqual(
            [dict(rev=self.doc2.rev, content=self.doc2.content),
             dict(rev=self.doc1.rev, content=self.doc1.content)],
            json.loads(cmd.stdout.getvalue()))
        self.assertEqual('', cmd.stderr.getvalue())

    def test_get_doc_conflicts_no_db(self):
        cmd = self.make_command(client.CmdGetDocConflicts)
        retval = cmd.run(self.db_path + "__DOES_NOT_EXIST", "my-doc")
        self.assertEqual(retval, 1)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual(cmd.stderr.getvalue(), 'Database does not exist.\n')

    def test_get_doc_conflicts_no_doc(self):
        cmd = self.make_command(client.CmdGetDocConflicts)
        retval = cmd.run(self.db_path, "some-doc")
        self.assertEqual(retval, 1)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual(cmd.stderr.getvalue(), 'Document does not exist.\n')


class TestCmdInit(TestCaseWithDB):

    def test_init_new(self):
        path = self.working_dir + '/test2.db'
        self.assertFalse(os.path.exists(path))
        cmd = self.make_command(client.CmdInitDB)
        cmd.run(path, 'test-uid')
        self.assertTrue(os.path.exists(path))
        db = u1db_open(path, create=False)
        self.assertEqual('test-uid', db._replica_uid)

    def test_init_no_uid(self):
        path = self.working_dir + '/test2.db'
        cmd = self.make_command(client.CmdInitDB)
        cmd.run(path, None)
        self.assertTrue(os.path.exists(path))
        db = u1db_open(path, create=False)
        self.assertIsNot(None, db._replica_uid)


class TestCmdPut(TestCaseWithDB):

    def setUp(self):
        super(TestCmdPut, self).setUp()
        self.doc = self.db.create_doc_from_json(
            tests.simple_doc, doc_id='my-test-doc')

    def test_put_simple(self):
        cmd = self.make_command(client.CmdPut)
        inf = cStringIO.StringIO(tests.nested_doc)
        cmd.run(self.db_path, 'my-test-doc', self.doc.rev, inf)
        doc = self.db.get_doc('my-test-doc')
        self.assertNotEqual(self.doc.rev, doc.rev)
        self.assertGetDoc(self.db, 'my-test-doc', doc.rev,
                          tests.nested_doc, False)
        self.assertEqual('', cmd.stdout.getvalue())
        self.assertEqual('rev: %s\n' % (doc.rev,),
                         cmd.stderr.getvalue())

    def test_put_no_db(self):
        cmd = self.make_command(client.CmdPut)
        inf = cStringIO.StringIO(tests.nested_doc)
        retval = cmd.run(self.db_path + "__DOES_NOT_EXIST",
                         'my-test-doc', self.doc.rev, inf)
        self.assertEqual(retval, 1)
        self.assertEqual('', cmd.stdout.getvalue())
        self.assertEqual('Database does not exist.\n', cmd.stderr.getvalue())

    def test_put_no_doc(self):
        cmd = self.make_command(client.CmdPut)
        inf = cStringIO.StringIO(tests.nested_doc)
        retval = cmd.run(self.db_path, 'no-such-doc', 'wut:1', inf)
        self.assertEqual(1, retval)
        self.assertEqual('', cmd.stdout.getvalue())
        self.assertEqual('Document does not exist.\n', cmd.stderr.getvalue())

    def test_put_doc_old_rev(self):
        rev = self.doc.rev
        doc = self.make_document('my-test-doc', rev, '{}', False)
        self.db.put_doc(doc)
        cmd = self.make_command(client.CmdPut)
        inf = cStringIO.StringIO(tests.nested_doc)
        retval = cmd.run(self.db_path, 'my-test-doc', rev, inf)
        self.assertEqual(1, retval)
        self.assertEqual('', cmd.stdout.getvalue())
        self.assertEqual('Given revision is not current.\n',
                         cmd.stderr.getvalue())

    def test_put_doc_w_conflicts(self):
        doc = self.make_document('my-test-doc', 'other:1', '{}', False)
        self.db._put_doc_if_newer(
            doc, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        cmd = self.make_command(client.CmdPut)
        inf = cStringIO.StringIO(tests.nested_doc)
        retval = cmd.run(self.db_path, 'my-test-doc', 'other:1', inf)
        self.assertEqual(1, retval)
        self.assertEqual('', cmd.stdout.getvalue())
        self.assertEqual('Document has conflicts.\n'
                         'Inspect with get-doc-conflicts, then resolve.\n',
                         cmd.stderr.getvalue())


class TestCmdResolve(TestCaseWithDB):

    def setUp(self):
        super(TestCmdResolve, self).setUp()
        self.doc1 = self.db.create_doc_from_json(
            tests.simple_doc, doc_id='my-doc')
        self.doc2 = self.make_document('my-doc', 'other:1', '{}', False)
        self.db._put_doc_if_newer(
            self.doc2, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')

    def test_resolve_simple(self):
        self.assertTrue(self.db.get_doc('my-doc').has_conflicts)
        cmd = self.make_command(client.CmdResolve)
        inf = cStringIO.StringIO(tests.nested_doc)
        cmd.run(self.db_path, 'my-doc', [self.doc1.rev, self.doc2.rev], inf)
        doc = self.db.get_doc('my-doc')
        vec = vectorclock.VectorClockRev(doc.rev)
        self.assertTrue(
            vec.is_newer(vectorclock.VectorClockRev(self.doc1.rev)))
        self.assertTrue(
            vec.is_newer(vectorclock.VectorClockRev(self.doc2.rev)))
        self.assertGetDoc(self.db, 'my-doc', doc.rev, tests.nested_doc, False)
        self.assertEqual('', cmd.stdout.getvalue())
        self.assertEqual('rev: %s\n' % (doc.rev,),
                         cmd.stderr.getvalue())

    def test_resolve_double(self):
        moar = '{"x": 42}'
        doc3 = self.make_document('my-doc', 'third:1', moar, False)
        self.db._put_doc_if_newer(
            doc3, save_conflict=True, replica_uid='r', replica_gen=1,
            replica_trans_id='foo')
        cmd = self.make_command(client.CmdResolve)
        inf = cStringIO.StringIO(tests.nested_doc)
        cmd.run(self.db_path, 'my-doc', [self.doc1.rev, self.doc2.rev], inf)
        doc = self.db.get_doc('my-doc')
        self.assertGetDoc(self.db, 'my-doc', doc.rev, moar, True)
        self.assertEqual('', cmd.stdout.getvalue())
        self.assertEqual(
            'rev: %s\nDocument still has conflicts.\n' % (doc.rev,),
            cmd.stderr.getvalue())

    def test_resolve_no_db(self):
        cmd = self.make_command(client.CmdResolve)
        retval = cmd.run(self.db_path + "__DOES_NOT_EXIST", "my-doc", [], None)
        self.assertEqual(retval, 1)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual(cmd.stderr.getvalue(), 'Database does not exist.\n')

    def test_resolve_no_doc(self):
        cmd = self.make_command(client.CmdResolve)
        retval = cmd.run(self.db_path, "foo", [], None)
        self.assertEqual(retval, 1)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual(cmd.stderr.getvalue(), 'Document does not exist.\n')


class TestCmdSync(TestCaseWithDB):

    def setUp(self):
        super(TestCmdSync, self).setUp()
        self.db2_path = self.working_dir + '/test2.db'
        self.db2 = u1db_open(self.db2_path, create=True)
        self.addCleanup(self.db2.close)
        self.db2._set_replica_uid('test2')
        self.doc = self.db.create_doc_from_json(
            tests.simple_doc, doc_id='test-id')
        self.doc2 = self.db2.create_doc_from_json(
            tests.nested_doc, doc_id='my-test-id')

    def test_sync(self):
        cmd = self.make_command(client.CmdSync)
        cmd.run(self.db_path, self.db2_path)
        self.assertGetDoc(self.db2, 'test-id', self.doc.rev, tests.simple_doc,
                          False)
        self.assertGetDoc(self.db, 'my-test-id', self.doc2.rev,
                          tests.nested_doc, False)


class TestCmdSyncRemote(tests.TestCaseWithServer, TestCaseWithDB):

    make_app_with_state = \
                        staticmethod(test_remote_sync_target.make_http_app)

    def setUp(self):
        super(TestCmdSyncRemote, self).setUp()
        self.startServer()
        self.db2 = self.request_state._create_database('test2.db')

    def test_sync_remote(self):
        doc1 = self.db.create_doc_from_json(tests.simple_doc)
        doc2 = self.db2.create_doc_from_json(tests.nested_doc)
        db2_url = self.getURL('test2.db')
        self.assertTrue(db2_url.startswith('http://'))
        self.assertTrue(db2_url.endswith('/test2.db'))
        cmd = self.make_command(client.CmdSync)
        cmd.run(self.db_path, db2_url)
        self.assertGetDoc(self.db2, doc1.doc_id, doc1.rev, tests.simple_doc,
                          False)
        self.assertGetDoc(self.db, doc2.doc_id, doc2.rev, tests.nested_doc,
                          False)


class TestCmdCreateIndex(TestCaseWithDB):

    def test_create_index(self):
        cmd = self.make_command(client.CmdCreateIndex)
        retval = cmd.run(self.db_path, "foo", ["bar", "baz"])
        self.assertEqual(self.db.list_indexes(), [('foo', ['bar', "baz"])])
        self.assertEqual(retval, None)  # conveniently mapped to 0
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual(cmd.stderr.getvalue(), '')

    def test_create_index_no_db(self):
        cmd = self.make_command(client.CmdCreateIndex)
        retval = cmd.run(self.db_path + "__DOES_NOT_EXIST", "foo", ["bar"])
        self.assertEqual(retval, 1)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual(cmd.stderr.getvalue(), 'Database does not exist.\n')

    def test_create_dupe_index(self):
        self.db.create_index("foo", "bar")
        cmd = self.make_command(client.CmdCreateIndex)
        retval = cmd.run(self.db_path, "foo", ["bar"])
        self.assertEqual(retval, None)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual(cmd.stderr.getvalue(), '')

    def test_create_dupe_index_different_expression(self):
        self.db.create_index("foo", "bar")
        cmd = self.make_command(client.CmdCreateIndex)
        retval = cmd.run(self.db_path, "foo", ["baz"])
        self.assertEqual(retval, 1)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual(cmd.stderr.getvalue(),
                         "There is already a different index named 'foo'.\n")

    def test_create_index_bad_expression(self):
        cmd = self.make_command(client.CmdCreateIndex)
        retval = cmd.run(self.db_path, "foo", ["WAT()"])
        self.assertEqual(retval, 1)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual(cmd.stderr.getvalue(),
                         'Bad index expression.\n')


class TestCmdListIndexes(TestCaseWithDB):

    def test_list_no_indexes(self):
        cmd = self.make_command(client.CmdListIndexes)
        retval = cmd.run(self.db_path)
        self.assertEqual(retval, None)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual(cmd.stderr.getvalue(), '')

    def test_list_indexes(self):
        self.db.create_index("foo", "bar", "baz")
        cmd = self.make_command(client.CmdListIndexes)
        retval = cmd.run(self.db_path)
        self.assertEqual(retval, None)
        self.assertEqual(cmd.stdout.getvalue(), 'foo: bar, baz\n')
        self.assertEqual(cmd.stderr.getvalue(), '')

    def test_list_several_indexes(self):
        self.db.create_index("foo", "bar", "baz")
        self.db.create_index("bar", "baz", "foo")
        self.db.create_index("baz", "foo", "bar")
        cmd = self.make_command(client.CmdListIndexes)
        retval = cmd.run(self.db_path)
        self.assertEqual(retval, None)
        self.assertEqual(cmd.stdout.getvalue(),
                         'bar: baz, foo\n'
                         'baz: foo, bar\n'
                         'foo: bar, baz\n'
                         )
        self.assertEqual(cmd.stderr.getvalue(), '')

    def test_list_indexes_no_db(self):
        cmd = self.make_command(client.CmdListIndexes)
        retval = cmd.run(self.db_path + "__DOES_NOT_EXIST")
        self.assertEqual(retval, 1)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual(cmd.stderr.getvalue(), 'Database does not exist.\n')


class TestCmdDeleteIndex(TestCaseWithDB):

    def test_delete_index(self):
        self.db.create_index("foo", "bar", "baz")
        cmd = self.make_command(client.CmdDeleteIndex)
        retval = cmd.run(self.db_path, "foo")
        self.assertEqual(retval, None)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual(cmd.stderr.getvalue(), '')
        self.assertEqual([], self.db.list_indexes())

    def test_delete_index_no_db(self):
        cmd = self.make_command(client.CmdDeleteIndex)
        retval = cmd.run(self.db_path + "__DOES_NOT_EXIST", "foo")
        self.assertEqual(retval, 1)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual(cmd.stderr.getvalue(), 'Database does not exist.\n')

    def test_delete_index_no_index(self):
        cmd = self.make_command(client.CmdDeleteIndex)
        retval = cmd.run(self.db_path, "foo")
        self.assertEqual(retval, None)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual(cmd.stderr.getvalue(), '')


class TestCmdGetIndexKeys(TestCaseWithDB):

    def test_get_index_keys(self):
        self.db.create_index("foo", "bar")
        self.db.create_doc_from_json('{"bar": 42}')
        cmd = self.make_command(client.CmdGetIndexKeys)
        retval = cmd.run(self.db_path, "foo")
        self.assertEqual(retval, None)
        self.assertEqual(cmd.stdout.getvalue(), '42\n')
        self.assertEqual(cmd.stderr.getvalue(), '')

    def test_get_index_keys_nonascii(self):
        self.db.create_index("foo", "bar")
        self.db.create_doc_from_json('{"bar": "\u00a4"}')
        cmd = self.make_command(client.CmdGetIndexKeys)
        retval = cmd.run(self.db_path, "foo")
        self.assertEqual(retval, None)
        self.assertEqual(cmd.stdout.getvalue(), '\xc2\xa4\n')
        self.assertEqual(cmd.stderr.getvalue(), '')

    def test_get_index_keys_empty(self):
        self.db.create_index("foo", "bar")
        cmd = self.make_command(client.CmdGetIndexKeys)
        retval = cmd.run(self.db_path, "foo")
        self.assertEqual(retval, None)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual(cmd.stderr.getvalue(), '')

    def test_get_index_keys_no_db(self):
        cmd = self.make_command(client.CmdGetIndexKeys)
        retval = cmd.run(self.db_path + "__DOES_NOT_EXIST", "foo")
        self.assertEqual(retval, 1)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual(cmd.stderr.getvalue(), 'Database does not exist.\n')

    def test_get_index_keys_no_index(self):
        cmd = self.make_command(client.CmdGetIndexKeys)
        retval = cmd.run(self.db_path, "foo")
        self.assertEqual(retval, 1)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual(cmd.stderr.getvalue(), 'Index does not exist.\n')


class TestCmdGetFromIndex(TestCaseWithDB):

    def test_get_from_index(self):
        self.db.create_index("index", "key")
        doc1 = self.db.create_doc_from_json(tests.simple_doc)
        doc2 = self.db.create_doc_from_json(tests.nested_doc)
        cmd = self.make_command(client.CmdGetFromIndex)
        retval = cmd.run(self.db_path, "index", ["value"])
        self.assertEqual(retval, None)
        self.assertEqual(sorted(json.loads(cmd.stdout.getvalue())),
                         sorted([dict(id=doc1.doc_id,
                                      rev=doc1.rev,
                                      content=doc1.content),
                                 dict(id=doc2.doc_id,
                                      rev=doc2.rev,
                                      content=doc2.content),
                                 ]))
        self.assertEqual(cmd.stderr.getvalue(), '')

    def test_get_from_index_empty(self):
        self.db.create_index("index", "key")
        cmd = self.make_command(client.CmdGetFromIndex)
        retval = cmd.run(self.db_path, "index", ["value"])
        self.assertEqual(retval, None)
        self.assertEqual(cmd.stdout.getvalue(), '[]\n')
        self.assertEqual(cmd.stderr.getvalue(), '')

    def test_get_from_index_no_db(self):
        cmd = self.make_command(client.CmdGetFromIndex)
        retval = cmd.run(self.db_path + "__DOES_NOT_EXIST", "foo", [])
        self.assertEqual(retval, 1)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual(cmd.stderr.getvalue(), 'Database does not exist.\n')

    def test_get_from_index_no_index(self):
        cmd = self.make_command(client.CmdGetFromIndex)
        retval = cmd.run(self.db_path, "foo", [])
        self.assertEqual(retval, 1)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual(cmd.stderr.getvalue(), 'Index does not exist.\n')

    def test_get_from_index_two_expr_instead_of_one(self):
        self.db.create_index("index", "key1")
        cmd = self.make_command(client.CmdGetFromIndex)
        cmd.argv = ["XX", "YY"]
        retval = cmd.run(self.db_path, "index", ["value1", "value2"])
        self.assertEqual(retval, 1)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual("Invalid query: index 'index' requires"
                         " 1 query expression, not 2.\n"
                         "For example, the following would be valid:\n"
                         "    XX YY %r 'index' 'value1'\n"
                         % self.db_path, cmd.stderr.getvalue())

    def test_get_from_index_three_expr_instead_of_two(self):
        self.db.create_index("index", "key1", "key2")
        cmd = self.make_command(client.CmdGetFromIndex)
        cmd.argv = ["XX", "YY"]
        retval = cmd.run(self.db_path, "index", ["value1", "value2", "value3"])
        self.assertEqual(retval, 1)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual("Invalid query: index 'index' requires"
                         " 2 query expressions, not 3.\n"
                         "For example, the following would be valid:\n"
                         "    XX YY %r 'index' 'value1' 'value2'\n"
                         % self.db_path, cmd.stderr.getvalue())

    def test_get_from_index_one_expr_instead_of_two(self):
        self.db.create_index("index", "key1", "key2")
        cmd = self.make_command(client.CmdGetFromIndex)
        cmd.argv = ["XX", "YY"]
        retval = cmd.run(self.db_path, "index", ["value1"])
        self.assertEqual(retval, 1)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual("Invalid query: index 'index' requires"
                         " 2 query expressions, not 1.\n"
                         "For example, the following would be valid:\n"
                         "    XX YY %r 'index' 'value1' '*'\n"
                         % self.db_path, cmd.stderr.getvalue())

    def test_get_from_index_cant_bad_glob(self):
        self.db.create_index("index", "key1", "key2")
        cmd = self.make_command(client.CmdGetFromIndex)
        cmd.argv = ["XX", "YY"]
        retval = cmd.run(self.db_path, "index", ["value1*", "value2"])
        self.assertEqual(retval, 1)
        self.assertEqual(cmd.stdout.getvalue(), '')
        self.assertEqual("Invalid query:"
                         " a star can only be followed by stars.\n"
                         "For example, the following would be valid:\n"
                         "    XX YY %r 'index' 'value1*' '*'\n"
                         % self.db_path, cmd.stderr.getvalue())


class RunMainHelper(object):

    def run_main(self, args, stdin=None):
        if stdin is not None:
            self.patch(sys, 'stdin', cStringIO.StringIO(stdin))
        stdout = cStringIO.StringIO()
        stderr = cStringIO.StringIO()
        self.patch(sys, 'stdout', stdout)
        self.patch(sys, 'stderr', stderr)
        try:
            ret = client.main(args)
        except SystemExit, e:
            self.fail("Intercepted SystemExit: %s" % (e,))
        if ret is None:
            ret = 0
        return ret, stdout.getvalue(), stderr.getvalue()


class TestCommandLine(TestCaseWithDB, RunMainHelper):
    """These are meant to test that the infrastructure is fully connected.

    Each command is likely to only have one test here. Something that ensures
    'main()' knows about and can run the command correctly. Most logic-level
    testing of the Command should go into its own test class above.
    """

    def _get_u1db_client_path(self):
        from u1db import __path__ as u1db_path
        u1db_parent_dir = os.path.dirname(u1db_path[0])
        return os.path.join(u1db_parent_dir, 'u1db-client')

    def runU1DBClient(self, args):
        command = [sys.executable, self._get_u1db_client_path()]
        command.extend(args)
        p = subprocess.Popen(command, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(safe_close, p)
        return p

    def test_create_subprocess(self):
        p = self.runU1DBClient(['create', '--id', 'test-id', self.db_path])
        stdout, stderr = p.communicate(tests.simple_doc)
        self.assertEqual(0, p.returncode)
        self.assertEqual('', stdout)
        doc = self.db.get_doc('test-id')
        self.assertEqual(tests.simple_doc, doc.get_json())
        self.assertFalse(doc.has_conflicts)
        expected = 'id: test-id\nrev: %s\n' % (doc.rev,)
        stripped = stderr.replace('\r\n', '\n')
        if expected != stripped:
            # When run under python-dbg, it prints out the refs after the
            # actual content, so match it if we need to.
            expected_re = expected + '\[\d+ refs\]\n'
            self.assertRegexpMatches(stripped, expected_re)

    def test_get(self):
        doc = self.db.create_doc_from_json(tests.simple_doc, doc_id='test-id')
        ret, stdout, stderr = self.run_main(['get', self.db_path, 'test-id'])
        self.assertEqual(0, ret)
        self.assertEqual(tests.simple_doc + "\n", stdout)
        self.assertEqual('rev: %s\n' % (doc.rev,), stderr)
        ret, stdout, stderr = self.run_main(['get', self.db_path, 'not-there'])
        self.assertEqual(1, ret)

    def test_delete(self):
        doc = self.db.create_doc_from_json(tests.simple_doc, doc_id='test-id')
        ret, stdout, stderr = self.run_main(
            ['delete', self.db_path, 'test-id', doc.rev])
        doc = self.db.get_doc('test-id', include_deleted=True)
        self.assertEqual(0, ret)
        self.assertEqual('', stdout)
        self.assertEqual('rev: %s\n' % (doc.rev,), stderr)

    def test_init_db(self):
        path = self.working_dir + '/test2.db'
        ret, stdout, stderr = self.run_main(['init-db', path])
        u1db_open(path, create=False)

    def test_put(self):
        doc = self.db.create_doc_from_json(tests.simple_doc, doc_id='test-id')
        ret, stdout, stderr = self.run_main(
            ['put', self.db_path, 'test-id', doc.rev],
            stdin=tests.nested_doc)
        doc = self.db.get_doc('test-id')
        self.assertFalse(doc.has_conflicts)
        self.assertEqual(tests.nested_doc, doc.get_json())
        self.assertEqual(0, ret)
        self.assertEqual('', stdout)
        self.assertEqual('rev: %s\n' % (doc.rev,), stderr)

    def test_sync(self):
        doc = self.db.create_doc_from_json(tests.simple_doc, doc_id='test-id')
        self.db2_path = self.working_dir + '/test2.db'
        self.db2 = u1db_open(self.db2_path, create=True)
        self.addCleanup(self.db2.close)
        ret, stdout, stderr = self.run_main(
            ['sync', self.db_path, self.db2_path])
        self.assertEqual(0, ret)
        self.assertEqual('', stdout)
        self.assertEqual('', stderr)
        self.assertGetDoc(
            self.db2, 'test-id', doc.rev, tests.simple_doc, False)


class TestHTTPIntegration(tests.TestCaseWithServer, RunMainHelper):
    """Meant to test the cases where commands operate over http."""

    def server_def(self):
        def make_server(host_port, _application):
            return serve.make_server(host_port[0], host_port[1],
                                     self.working_dir)
        return make_server, "shutdown", "http"

    def setUp(self):
        super(TestHTTPIntegration, self).setUp()
        self.working_dir = self.createTempDir(prefix='u1db-http-server-')
        self.startServer()

    def getPath(self, dbname):
        return os.path.join(self.working_dir, dbname)

    def test_init_db(self):
        url = self.getURL('new.db')
        ret, stdout, stderr = self.run_main(['init-db', url])
        u1db_open(self.getPath('new.db'), create=False)

    def test_create_get_put_delete(self):
        db = u1db_open(self.getPath('test.db'), create=True)
        url = self.getURL('test.db')
        doc_id = '%abcd'
        ret, stdout, stderr = self.run_main(['create', url, '--id', doc_id],
                                            stdin=tests.simple_doc)
        self.assertEqual(0, ret)
        ret, stdout, stderr = self.run_main(['get', url, doc_id])
        self.assertEqual(0, ret)
        self.assertTrue(stderr.startswith('rev: '))
        doc_rev = stderr[len('rev: '):].rstrip()
        ret, stdout, stderr = self.run_main(['put', url, doc_id, doc_rev],
                                            stdin=tests.nested_doc)
        self.assertEqual(0, ret)
        self.assertTrue(stderr.startswith('rev: '))
        doc_rev1 = stderr[len('rev: '):].rstrip()
        self.assertGetDoc(db, doc_id, doc_rev1, tests.nested_doc, False)
        ret, stdout, stderr = self.run_main(['delete', url, doc_id, doc_rev1])
        self.assertEqual(0, ret)
        self.assertTrue(stderr.startswith('rev: '))
        doc_rev2 = stderr[len('rev: '):].rstrip()
        self.assertGetDocIncludeDeleted(db, doc_id, doc_rev2, None, False)
