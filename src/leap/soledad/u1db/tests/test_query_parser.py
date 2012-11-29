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

from u1db import (
    errors,
    query_parser,
    tests,
    )


trivial_raw_doc = {}


class TestFieldName(tests.TestCase):

    def test_check_fieldname_valid(self):
        self.assertIsNone(query_parser.check_fieldname("foo"))

    def test_check_fieldname_invalid(self):
        self.assertRaises(
            errors.IndexDefinitionParseError, query_parser.check_fieldname,
            "foo.")


class TestMakeTree(tests.TestCase):

    def setUp(self):
        super(TestMakeTree, self).setUp()
        self.parser = query_parser.Parser()

    def assertParseError(self, definition):
        self.assertRaises(
            errors.IndexDefinitionParseError, self.parser.parse,
            definition)

    def test_single_field(self):
        self.assertIsInstance(
            self.parser.parse('f'), query_parser.ExtractField)

    def test_single_mapping(self):
        self.assertIsInstance(
            self.parser.parse('bool(field1)'), query_parser.Bool)

    def test_nested_mapping(self):
        self.assertIsInstance(
            self.parser.parse('lower(split_words(field1))'),
            query_parser.Lower)

    def test_nested_branching_mapping(self):
        self.assertIsInstance(
            self.parser.parse(
                'combine(lower(field1), split_words(field2), '
                'number(field3, 5))'), query_parser.Combine)

    def test_single_mapping_multiple_fields(self):
        self.assertIsInstance(
            self.parser.parse('number(field1, 5)'), query_parser.Number)

    def test_unknown_mapping(self):
        self.assertParseError('mapping(whatever)')

    def test_parse_missing_close_paren(self):
        self.assertParseError("lower(a")

    def test_parse_trailing_chars(self):
        self.assertParseError("lower(ab))")

    def test_parse_empty_op(self):
        self.assertParseError("(ab)")

    def test_parse_top_level_commas(self):
        self.assertParseError("a, b")

    def test_invalid_field_name(self):
        self.assertParseError("a.")

    def test_invalid_inner_field_name(self):
        self.assertParseError("lower(a.)")

    def test_gobbledigook(self):
        self.assertParseError("(@#@cc   @#!*DFJSXV(()jccd")

    def test_leading_space(self):
        self.assertIsInstance(
            self.parser.parse("  lower(a)"), query_parser.Lower)

    def test_trailing_space(self):
        self.assertIsInstance(
            self.parser.parse("lower(a)  "), query_parser.Lower)

    def test_spaces_before_open_paren(self):
        self.assertIsInstance(
            self.parser.parse("lower  (a)"), query_parser.Lower)

    def test_spaces_after_open_paren(self):
        self.assertIsInstance(
            self.parser.parse("lower(  a)"), query_parser.Lower)

    def test_spaces_before_close_paren(self):
        self.assertIsInstance(
            self.parser.parse("lower(a  )"), query_parser.Lower)

    def test_spaces_before_comma(self):
        self.assertIsInstance(
            self.parser.parse("number(a  , 5)"), query_parser.Number)

    def test_spaces_after_comma(self):
        self.assertIsInstance(
            self.parser.parse("number(a,  5)"), query_parser.Number)


class TestStaticGetter(tests.TestCase):

    def test_returns_string(self):
        getter = query_parser.StaticGetter('foo')
        self.assertEqual(['foo'], getter.get(trivial_raw_doc))

    def test_returns_int(self):
        getter = query_parser.StaticGetter(9)
        self.assertEqual([9], getter.get(trivial_raw_doc))

    def test_returns_float(self):
        getter = query_parser.StaticGetter(9.2)
        self.assertEqual([9.2], getter.get(trivial_raw_doc))

    def test_returns_None(self):
        getter = query_parser.StaticGetter(None)
        self.assertEqual([], getter.get(trivial_raw_doc))

    def test_returns_list(self):
        getter = query_parser.StaticGetter(['a', 'b'])
        self.assertEqual(['a', 'b'], getter.get(trivial_raw_doc))


class TestExtractField(tests.TestCase):

    def assertExtractField(self, expected, field_name, raw_doc):
        getter = query_parser.ExtractField(field_name)
        self.assertEqual(expected, getter.get(raw_doc))

    def test_get_value(self):
        self.assertExtractField(['bar'], 'foo', {'foo': 'bar'})

    def test_get_value_None(self):
        self.assertExtractField([], 'foo', {'foo': None})

    def test_get_value_missing_key(self):
        self.assertExtractField([], 'foo', {})

    def test_get_value_subfield(self):
        self.assertExtractField(['bar'], 'foo.baz', {'foo': {'baz': 'bar'}})

    def test_get_value_subfield_missing(self):
        self.assertExtractField([], 'foo.baz', {'foo': 'bar'})

    def test_get_value_dict(self):
        self.assertExtractField([], 'foo', {'foo': {'baz': 'bar'}})

    def test_get_value_list(self):
        self.assertExtractField(['bar', 'zap'], 'foo', {'foo': ['bar', 'zap']})

    def test_get_value_mixed_list(self):
        self.assertExtractField(['bar', 'zap'], 'foo',
            {'foo': ['bar', ['baa'], 'zap', {'bing': 9}]})

    def test_get_value_list_of_dicts(self):
        self.assertExtractField([], 'foo', {'foo': [{'zap': 'bar'}]})

    def test_get_value_list_of_dicts2(self):
        self.assertExtractField(
            ['bar', 'baz'], 'foo.zap',
            {'foo': [{'zap': 'bar'}, {'zap': 'baz'}]})

    def test_get_value_int(self):
        self.assertExtractField([9], 'foo', {'foo': 9})

    def test_get_value_float(self):
        self.assertExtractField([9.2], 'foo', {'foo': 9.2})

    def test_get_value_bool(self):
        self.assertExtractField([True], 'foo', {'foo': True})
        self.assertExtractField([False], 'foo', {'foo': False})


class TestLower(tests.TestCase):

    def assertLowerGets(self, expected, input_val):
        getter = query_parser.Lower(query_parser.StaticGetter(input_val))
        out_val = getter.get(trivial_raw_doc)
        self.assertEqual(sorted(expected), sorted(out_val))

    def test_inner_returns_None(self):
        self.assertLowerGets([], None)

    def test_inner_returns_string(self):
        self.assertLowerGets(['foo'], 'fOo')

    def test_inner_returns_list(self):
        self.assertLowerGets(['foo', 'bar'], ['fOo', 'bAr'])

    def test_inner_returns_int(self):
        self.assertLowerGets([], 9)

    def test_inner_returns_float(self):
        self.assertLowerGets([], 9.0)

    def test_inner_returns_bool(self):
        self.assertLowerGets([], True)

    def test_inner_returns_list_containing_int(self):
        self.assertLowerGets(['foo', 'bar'], ['fOo', 9, 'bAr'])

    def test_inner_returns_list_containing_float(self):
        self.assertLowerGets(['foo', 'bar'], ['fOo', 9.2, 'bAr'])

    def test_inner_returns_list_containing_bool(self):
        self.assertLowerGets(['foo', 'bar'], ['fOo', True, 'bAr'])

    def test_inner_returns_list_containing_list(self):
        # TODO: Should this be unfolding the inner list?
        self.assertLowerGets(['foo', 'bar'], ['fOo', ['bAa'], 'bAr'])

    def test_inner_returns_list_containing_dict(self):
        self.assertLowerGets(['foo', 'bar'], ['fOo', {'baa': 'xam'}, 'bAr'])


class TestSplitWords(tests.TestCase):

    def assertSplitWords(self, expected, value):
        getter = query_parser.SplitWords(query_parser.StaticGetter(value))
        self.assertEqual(sorted(expected), sorted(getter.get(trivial_raw_doc)))

    def test_inner_returns_None(self):
        self.assertSplitWords([], None)

    def test_inner_returns_string(self):
        self.assertSplitWords(['foo', 'bar'], 'foo bar')

    def test_inner_returns_list(self):
        self.assertSplitWords(['foo', 'baz', 'bar', 'sux'],
                              ['foo baz', 'bar sux'])

    def test_deduplicates(self):
        self.assertSplitWords(['bar'], ['bar', 'bar', 'bar'])

    def test_inner_returns_int(self):
        self.assertSplitWords([], 9)

    def test_inner_returns_float(self):
        self.assertSplitWords([], 9.2)

    def test_inner_returns_bool(self):
        self.assertSplitWords([], True)

    def test_inner_returns_list_containing_int(self):
        self.assertSplitWords(['foo', 'baz', 'bar', 'sux'],
                              ['foo baz', 9, 'bar sux'])

    def test_inner_returns_list_containing_float(self):
        self.assertSplitWords(['foo', 'baz', 'bar', 'sux'],
                              ['foo baz', 9.2, 'bar sux'])

    def test_inner_returns_list_containing_bool(self):
        self.assertSplitWords(['foo', 'baz', 'bar', 'sux'],
                              ['foo baz', True, 'bar sux'])

    def test_inner_returns_list_containing_list(self):
        # TODO: Expand sub-lists?
        self.assertSplitWords(['foo', 'baz', 'bar', 'sux'],
                              ['foo baz', ['baa'], 'bar sux'])

    def test_inner_returns_list_containing_dict(self):
        self.assertSplitWords(['foo', 'baz', 'bar', 'sux'],
                              ['foo baz', {'baa': 'xam'}, 'bar sux'])


class TestNumber(tests.TestCase):

    def assertNumber(self, expected, value, padding=5):
        """Assert number transformation produced expected values."""
        getter = query_parser.Number(query_parser.StaticGetter(value), padding)
        self.assertEqual(expected, getter.get(trivial_raw_doc))

    def test_inner_returns_None(self):
        """None is thrown away."""
        self.assertNumber([], None)

    def test_inner_returns_int(self):
        """A single integer is converted to zero padded strings."""
        self.assertNumber(['00009'], 9)

    def test_inner_returns_list(self):
        """Integers are converted to zero padded strings."""
        self.assertNumber(['00009', '00235'], [9, 235])

    def test_inner_returns_string(self):
        """A string is thrown away."""
        self.assertNumber([], 'foo bar')

    def test_inner_returns_float(self):
        """A float is thrown away."""
        self.assertNumber([], 9.2)

    def test_inner_returns_bool(self):
        """A boolean is thrown away."""
        self.assertNumber([], True)

    def test_inner_returns_list_containing_strings(self):
        """Strings in a list are thrown away."""
        self.assertNumber(['00009'], ['foo baz', 9, 'bar sux'])

    def test_inner_returns_list_containing_float(self):
        """Floats in a list are thrown away."""
        self.assertNumber(
            ['00083', '00073'], [83, 9.2, 73])

    def test_inner_returns_list_containing_bool(self):
        """Booleans in a list are thrown away."""
        self.assertNumber(
            ['00083', '00073'], [83, True, 73])

    def test_inner_returns_list_containing_list(self):
        """Lists in a list are thrown away."""
        # TODO: Expand sub-lists?
        self.assertNumber(
            ['00012', '03333'], [12, [29], 3333])

    def test_inner_returns_list_containing_dict(self):
        """Dicts in a list are thrown away."""
        self.assertNumber(
            ['00012', '00001'], [12, {54: 89}, 1])


class TestIsNull(tests.TestCase):

    def assertIsNull(self, value):
        getter = query_parser.IsNull(query_parser.StaticGetter(value))
        self.assertEqual([True], getter.get(trivial_raw_doc))

    def assertIsNotNull(self, value):
        getter = query_parser.IsNull(query_parser.StaticGetter(value))
        self.assertEqual([False], getter.get(trivial_raw_doc))

    def test_inner_returns_None(self):
        self.assertIsNull(None)

    def test_inner_returns_string(self):
        self.assertIsNotNull('foo')

    def test_inner_returns_list(self):
        self.assertIsNotNull(['foo', 'bar'])

    def test_inner_returns_empty_list(self):
        # TODO: is this the behavior we want?
        self.assertIsNull([])

    def test_inner_returns_int(self):
        self.assertIsNotNull(9)

    def test_inner_returns_float(self):
        self.assertIsNotNull(9.2)

    def test_inner_returns_bool(self):
        self.assertIsNotNull(True)

    # TODO: What about a dict? Inner is likely to return None, even though the
    #       attribute does exist...


class TestParser(tests.TestCase):

    def parse(self, spec):
        parser = query_parser.Parser()
        return parser.parse(spec)

    def parse_all(self, specs):
        parser = query_parser.Parser()
        return parser.parse_all(specs)

    def assertParseError(self, definition):
        self.assertRaises(errors.IndexDefinitionParseError, self.parse,
                          definition)

    def test_parse_empty_string(self):
        self.assertRaises(errors.IndexDefinitionParseError, self.parse, "")

    def test_parse_field(self):
        getter = self.parse("a")
        self.assertIsInstance(getter, query_parser.ExtractField)
        self.assertEqual(["a"], getter.field)

    def test_parse_dotted_field(self):
        getter = self.parse("a.b")
        self.assertIsInstance(getter, query_parser.ExtractField)
        self.assertEqual(["a", "b"], getter.field)

    def test_parse_dotted_field_nothing_after_dot(self):
        self.assertParseError("a.")

    def test_parse_missing_close_on_transformation(self):
        self.assertParseError("lower(a")

    def test_parse_missing_field_in_transformation(self):
        self.assertParseError("lower()")

    def test_parse_trailing_chars(self):
        self.assertParseError("lower(ab))")

    def test_parse_empty_op(self):
        self.assertParseError("(ab)")

    def test_parse_unknown_op(self):
        self.assertParseError("no_such_operation(field)")

    def test_parse_wrong_arg_type(self):
        self.assertParseError("number(field, fnord)")

    def test_parse_transformation(self):
        getter = self.parse("lower(a)")
        self.assertIsInstance(getter, query_parser.Lower)
        self.assertIsInstance(getter.inner, query_parser.ExtractField)
        self.assertEqual(["a"], getter.inner.field)

    def test_parse_all(self):
        getters = self.parse_all(["a", "b"])
        self.assertEqual(2, len(getters))
        self.assertIsInstance(getters[0], query_parser.ExtractField)
        self.assertEqual(["a"], getters[0].field)
        self.assertIsInstance(getters[1], query_parser.ExtractField)
        self.assertEqual(["b"], getters[1].field)
