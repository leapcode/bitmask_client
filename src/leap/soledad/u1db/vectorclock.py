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

"""VectorClockRev helper class."""


class VectorClockRev(object):
    """Track vector clocks for multiple replica ids.

    This allows simple comparison to determine if one VectorClockRev is
    newer/older/in-conflict-with another VectorClockRev without having to
    examine history. Every replica has a strictly increasing revision. When
    creating a new revision, they include all revisions for all other replicas
    which the new revision dominates, and increment their own revision to
    something greater than the current value.
    """

    def __init__(self, value):
        self._values = self._expand(value)

    def __repr__(self):
        s = self.as_str()
        return '%s(%s)' % (self.__class__.__name__, s)

    def as_str(self):
        s = '|'.join(['%s:%d' % (m, r) for m, r
                      in sorted(self._values.items())])
        return s

    def _expand(self, value):
        result = {}
        if value is None:
            return result
        for replica_info in value.split('|'):
            replica_uid, counter = replica_info.split(':')
            counter = int(counter)
            result[replica_uid] = counter
        return result

    def is_newer(self, other):
        """Is this VectorClockRev strictly newer than other.
        """
        if not self._values:
            return False
        if not other._values:
            return True
        this_is_newer = False
        other_expand = dict(other._values)
        for key, value in self._values.iteritems():
            if key in other_expand:
                other_value = other_expand.pop(key)
                if other_value > value:
                    return False
                elif other_value < value:
                    this_is_newer = True
            else:
                this_is_newer = True
        if other_expand:
            return False
        return this_is_newer

    def increment(self, replica_uid):
        """Increase the 'replica_uid' section of this vector clock.

        :return: A string representing the new vector clock value
        """
        self._values[replica_uid] = self._values.get(replica_uid, 0) + 1

    def maximize(self, other_vcr):
        for replica_uid, counter in other_vcr._values.iteritems():
            if replica_uid not in self._values:
                self._values[replica_uid] = counter
            else:
                this_counter = self._values[replica_uid]
                if this_counter < counter:
                    self._values[replica_uid] = counter
