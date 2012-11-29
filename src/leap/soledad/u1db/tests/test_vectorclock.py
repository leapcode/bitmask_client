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

"""VectorClockRev helper class tests."""

from u1db import tests, vectorclock

try:
    from u1db.tests import c_backend_wrapper
except ImportError:
    c_backend_wrapper = None


c_vectorclock_scenarios = []
if c_backend_wrapper is not None:
    c_vectorclock_scenarios.append(
        ('c', {'create_vcr': c_backend_wrapper.VectorClockRev}))


class TestVectorClockRev(tests.TestCase):

    scenarios = [('py', {'create_vcr': vectorclock.VectorClockRev})
            ] + c_vectorclock_scenarios

    def assertIsNewer(self, newer_rev, older_rev):
        new_vcr = self.create_vcr(newer_rev)
        old_vcr = self.create_vcr(older_rev)
        self.assertTrue(new_vcr.is_newer(old_vcr))
        self.assertFalse(old_vcr.is_newer(new_vcr))

    def assertIsConflicted(self, rev_a, rev_b):
        vcr_a = self.create_vcr(rev_a)
        vcr_b = self.create_vcr(rev_b)
        self.assertFalse(vcr_a.is_newer(vcr_b))
        self.assertFalse(vcr_b.is_newer(vcr_a))

    def assertRoundTrips(self, rev):
        self.assertEqual(rev, self.create_vcr(rev).as_str())

    def test__is_newer_doc_rev(self):
        self.assertIsNewer('test:1', None)
        self.assertIsNewer('test:2', 'test:1')
        self.assertIsNewer('other:2|test:1', 'other:1|test:1')
        self.assertIsNewer('other:1|test:1', 'other:1')
        self.assertIsNewer('a:2|b:1', 'b:1')
        self.assertIsNewer('a:1|b:2', 'a:1')
        self.assertIsConflicted('other:2|test:1', 'other:1|test:2')
        self.assertIsConflicted('other:1|test:1', 'other:2')
        self.assertIsConflicted('test:1', 'test:1')

    def test_None(self):
        vcr = self.create_vcr(None)
        self.assertEqual('', vcr.as_str())

    def test_round_trips(self):
        self.assertRoundTrips('test:1')
        self.assertRoundTrips('a:1|b:2')
        self.assertRoundTrips('alternate:2|test:1')

    def test_handles_sort_order(self):
        self.assertEqual('a:1|b:2', self.create_vcr('b:2|a:1').as_str())
        # Last one out of place
        self.assertEqual('a:1|b:2|c:3|d:4|e:5|f:6',
                self.create_vcr('f:6|a:1|b:2|c:3|d:4|e:5').as_str())
        # Fully reversed
        self.assertEqual('a:1|b:2|c:3|d:4|e:5|f:6',
                self.create_vcr('f:6|e:5|d:4|c:3|b:2|a:1').as_str())

    def assertIncrement(self, original, replica_uid, after_increment):
        vcr = self.create_vcr(original)
        vcr.increment(replica_uid)
        self.assertEqual(after_increment, vcr.as_str())

    def test_increment(self):
        self.assertIncrement(None, 'test', 'test:1')
        self.assertIncrement('test:1', 'test', 'test:2')

    def test_increment_adds_uid(self):
        self.assertIncrement('other:1', 'test', 'other:1|test:1')
        self.assertIncrement('a:1|ab:2', 'aa', 'a:1|aa:1|ab:2')

    def test_increment_update_partial(self):
        self.assertIncrement('a:1|ab:2', 'a', 'a:2|ab:2')
        self.assertIncrement('a:2|ab:2', 'ab', 'a:2|ab:3')

    def test_increment_appends_uid(self):
        self.assertIncrement('b:2', 'c', 'b:2|c:1')

    def assertMaximize(self, rev1, rev2, maximized):
        vcr1 = self.create_vcr(rev1)
        vcr2 = self.create_vcr(rev2)
        vcr1.maximize(vcr2)
        self.assertEqual(maximized, vcr1.as_str())
        # reset vcr1 to maximize the other way
        vcr1 = self.create_vcr(rev1)
        vcr2.maximize(vcr1)
        self.assertEqual(maximized, vcr2.as_str())

    def test_maximize(self):
        self.assertMaximize(None, None, '')
        self.assertMaximize(None, 'x:1', 'x:1')
        self.assertMaximize('x:1', 'y:1', 'x:1|y:1')
        self.assertMaximize('x:2', 'x:1', 'x:2')
        self.assertMaximize('x:2', 'x:1|y:2', 'x:2|y:2')
        self.assertMaximize('a:1|c:2|e:3', 'b:3|d:4|f:5',
                            'a:1|b:3|c:2|d:4|e:3|f:5')

load_tests = tests.load_with_scenarios
