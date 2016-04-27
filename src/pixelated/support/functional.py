#
# Copyright (c) 2014 ThoughtWorks, Inc.
#
# Pixelated is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pixelated is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Pixelated. If not, see <http://www.gnu.org/licenses/>.
from itertools import chain


def flatten(_list):
    return list(chain.from_iterable(_list))


def unique(_list):
    seen = set()
    seen_add = seen.add
    return [x for x in _list if not (x in seen or seen_add(x))]


def compact(_list):
    return [a for a in _list if a]


def to_unicode(text):
    if text and not isinstance(text, unicode):
        encoding = 'utf-8'
        return unicode(text, encoding=encoding)
    return text
