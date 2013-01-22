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


from u1db import errors

from leap.soledad.tests import u1db_tests as tests


class TestDocument(tests.TestCase):

    scenarios = ([(
        'py', {'make_document_for_test': tests.make_document_for_test})]) #+
        #tests.C_DATABASE_SCENARIOS)

    def test_create_doc(self):
        doc = self.make_document('doc-id', 'uid:1', tests.simple_doc)
        self.assertEqual('doc-id', doc.doc_id)
        self.assertEqual('uid:1', doc.rev)
        self.assertEqual(tests.simple_doc, doc.get_json())
        self.assertFalse(doc.has_conflicts)

    def test__repr__(self):
        doc = self.make_document('doc-id', 'uid:1', tests.simple_doc)
        self.assertEqual(
            '%s(doc-id, uid:1, \'{"key": "value"}\')'
                % (doc.__class__.__name__,),
            repr(doc))

    def test__repr__conflicted(self):
        doc = self.make_document('doc-id', 'uid:1', tests.simple_doc,
                                 has_conflicts=True)
        self.assertEqual(
            '%s(doc-id, uid:1, conflicted, \'{"key": "value"}\')'
                % (doc.__class__.__name__,),
            repr(doc))

    def test__lt__(self):
        doc_a = self.make_document('a', 'b', '{}')
        doc_b = self.make_document('b', 'b', '{}')
        self.assertTrue(doc_a < doc_b)
        self.assertTrue(doc_b > doc_a)
        doc_aa = self.make_document('a', 'a', '{}')
        self.assertTrue(doc_aa < doc_a)

    def test__eq__(self):
        doc_a = self.make_document('a', 'b', '{}')
        doc_b = self.make_document('a', 'b', '{}')
        self.assertTrue(doc_a == doc_b)
        doc_b = self.make_document('a', 'b', '{}', has_conflicts=True)
        self.assertFalse(doc_a == doc_b)

    def test_non_json_dict(self):
        self.assertRaises(
            errors.InvalidJSON, self.make_document, 'id', 'uid:1',
            '"not a json dictionary"')

    def test_non_json(self):
        self.assertRaises(
            errors.InvalidJSON, self.make_document, 'id', 'uid:1',
            'not a json dictionary')

    def test_get_size(self):
        doc_a = self.make_document('a', 'b', '{"some": "content"}')
        self.assertEqual(
            len('a' + 'b' + '{"some": "content"}'), doc_a.get_size())

    def test_get_size_empty_document(self):
        doc_a = self.make_document('a', 'b', None)
        self.assertEqual(len('a' + 'b'), doc_a.get_size())


class TestPyDocument(tests.TestCase):

    scenarios = ([(
        'py', {'make_document_for_test': tests.make_document_for_test})])

    def test_get_content(self):
        doc = self.make_document('id', 'rev', '{"content":""}')
        self.assertEqual({"content": ""}, doc.content)
        doc.set_json('{"content": "new"}')
        self.assertEqual({"content": "new"}, doc.content)

    def test_set_content(self):
        doc = self.make_document('id', 'rev', '{"content":""}')
        doc.content = {"content": "new"}
        self.assertEqual('{"content": "new"}', doc.get_json())

    def test_set_bad_content(self):
        doc = self.make_document('id', 'rev', '{"content":""}')
        self.assertRaises(
            errors.InvalidContent, setattr, doc, 'content',
            '{"content": "new"}')

    def test_is_tombstone(self):
        doc_a = self.make_document('a', 'b', '{}')
        self.assertFalse(doc_a.is_tombstone())
        doc_a.set_json(None)
        self.assertTrue(doc_a.is_tombstone())

    def test_make_tombstone(self):
        doc_a = self.make_document('a', 'b', '{}')
        self.assertFalse(doc_a.is_tombstone())
        doc_a.make_tombstone()
        self.assertTrue(doc_a.is_tombstone())

    def test_same_content_as(self):
        doc_a = self.make_document('a', 'b', '{}')
        doc_b = self.make_document('d', 'e', '{}')
        self.assertTrue(doc_a.same_content_as(doc_b))
        doc_b = self.make_document('p', 'q', '{}', has_conflicts=True)
        self.assertTrue(doc_a.same_content_as(doc_b))
        doc_b.content['key'] = 'value'
        self.assertFalse(doc_a.same_content_as(doc_b))

    def test_same_content_as_json_order(self):
        doc_a = self.make_document(
            'a', 'b', '{"key1": "val1", "key2": "val2"}')
        doc_b = self.make_document(
            'c', 'd', '{"key2": "val2", "key1": "val1"}')
        self.assertTrue(doc_a.same_content_as(doc_b))

    def test_set_json(self):
        doc = self.make_document('id', 'rev', '{"content":""}')
        doc.set_json('{"content": "new"}')
        self.assertEqual('{"content": "new"}', doc.get_json())

    def test_set_json_non_dict(self):
        doc = self.make_document('id', 'rev', '{"content":""}')
        self.assertRaises(errors.InvalidJSON, doc.set_json, '"is not a dict"')

    def test_set_json_error(self):
        doc = self.make_document('id', 'rev', '{"content":""}')
        self.assertRaises(errors.InvalidJSON, doc.set_json, 'is not json')


load_tests = tests.load_with_scenarios
