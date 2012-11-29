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

"""Test in-memory backend internals."""

from u1db import (
    errors,
    tests,
    )
from u1db.backends import inmemory


simple_doc = '{"key": "value"}'


class TestInMemoryDatabaseInternals(tests.TestCase):

    def setUp(self):
        super(TestInMemoryDatabaseInternals, self).setUp()
        self.db = inmemory.InMemoryDatabase('test')

    def test__allocate_doc_rev_from_None(self):
        self.assertEqual('test:1', self.db._allocate_doc_rev(None))

    def test__allocate_doc_rev_incremental(self):
        self.assertEqual('test:2', self.db._allocate_doc_rev('test:1'))

    def test__allocate_doc_rev_other(self):
        self.assertEqual('replica:1|test:1',
                         self.db._allocate_doc_rev('replica:1'))

    def test__get_replica_uid(self):
        self.assertEqual('test', self.db._replica_uid)


class TestInMemoryIndex(tests.TestCase):

    def test_has_name_and_definition(self):
        idx = inmemory.InMemoryIndex('idx-name', ['key'])
        self.assertEqual('idx-name', idx._name)
        self.assertEqual(['key'], idx._definition)

    def test_evaluate_json(self):
        idx = inmemory.InMemoryIndex('idx-name', ['key'])
        self.assertEqual(['value'], idx.evaluate_json(simple_doc))

    def test_evaluate_json_field_None(self):
        idx = inmemory.InMemoryIndex('idx-name', ['missing'])
        self.assertEqual([], idx.evaluate_json(simple_doc))

    def test_evaluate_json_subfield_None(self):
        idx = inmemory.InMemoryIndex('idx-name', ['key', 'missing'])
        self.assertEqual([], idx.evaluate_json(simple_doc))

    def test_evaluate_multi_index(self):
        doc = '{"key": "value", "key2": "value2"}'
        idx = inmemory.InMemoryIndex('idx-name', ['key', 'key2'])
        self.assertEqual(['value\x01value2'],
                         idx.evaluate_json(doc))

    def test_update_ignores_None(self):
        idx = inmemory.InMemoryIndex('idx-name', ['nokey'])
        idx.add_json('doc-id', simple_doc)
        self.assertEqual({}, idx._values)

    def test_update_adds_entry(self):
        idx = inmemory.InMemoryIndex('idx-name', ['key'])
        idx.add_json('doc-id', simple_doc)
        self.assertEqual({'value': ['doc-id']}, idx._values)

    def test_remove_json(self):
        idx = inmemory.InMemoryIndex('idx-name', ['key'])
        idx.add_json('doc-id', simple_doc)
        self.assertEqual({'value': ['doc-id']}, idx._values)
        idx.remove_json('doc-id', simple_doc)
        self.assertEqual({}, idx._values)

    def test_remove_json_multiple(self):
        idx = inmemory.InMemoryIndex('idx-name', ['key'])
        idx.add_json('doc-id', simple_doc)
        idx.add_json('doc2-id', simple_doc)
        self.assertEqual({'value': ['doc-id', 'doc2-id']}, idx._values)
        idx.remove_json('doc-id', simple_doc)
        self.assertEqual({'value': ['doc2-id']}, idx._values)

    def test_keys(self):
        idx = inmemory.InMemoryIndex('idx-name', ['key'])
        idx.add_json('doc-id', simple_doc)
        self.assertEqual(['value'], idx.keys())

    def test_lookup(self):
        idx = inmemory.InMemoryIndex('idx-name', ['key'])
        idx.add_json('doc-id', simple_doc)
        self.assertEqual(['doc-id'], idx.lookup(['value']))

    def test_lookup_multi(self):
        idx = inmemory.InMemoryIndex('idx-name', ['key'])
        idx.add_json('doc-id', simple_doc)
        idx.add_json('doc2-id', simple_doc)
        self.assertEqual(['doc-id', 'doc2-id'], idx.lookup(['value']))

    def test__find_non_wildcards(self):
        idx = inmemory.InMemoryIndex('idx-name', ['k1', 'k2', 'k3'])
        self.assertEqual(-1, idx._find_non_wildcards(('a', 'b', 'c')))
        self.assertEqual(2, idx._find_non_wildcards(('a', 'b', '*')))
        self.assertEqual(3, idx._find_non_wildcards(('a', 'b', 'c*')))
        self.assertEqual(2, idx._find_non_wildcards(('a', 'b*', '*')))
        self.assertEqual(0, idx._find_non_wildcards(('*', '*', '*')))
        self.assertEqual(1, idx._find_non_wildcards(('a*', '*', '*')))
        self.assertRaises(errors.InvalidValueForIndex,
            idx._find_non_wildcards, ('a', 'b'))
        self.assertRaises(errors.InvalidValueForIndex,
            idx._find_non_wildcards, ('a', 'b', 'c', 'd'))
        self.assertRaises(errors.InvalidGlobbing,
            idx._find_non_wildcards, ('*', 'b', 'c'))
