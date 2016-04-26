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

import json


class Tag(object):

    @classmethod
    def from_dict(cls, tag_dict):
        tag = Tag(tag_dict['name'], tag_dict['default'])
        tag.mails = set(tag_dict['mails'])
        return tag

    @classmethod
    def from_json_string(cls, json_string):
        tag_dict = json.loads(json_string)
        tag_dict['mails'] = set(tag_dict['mails'])
        return Tag.from_dict(tag_dict)

    @property
    def total(self):
        return len(self.mails)

    def __init__(self, name, default=False):
        self.name = name.lower()
        self.ident = self.name.__hash__()
        self.default = default
        self.mails = set()

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return self.name.__hash__()

    def increment(self, mail_ident):
        self.mails.add(mail_ident)

    def decrement(self, mail_ident):
        self.mails.discard(mail_ident)

    def as_dict(self):
        return {
            'name': self.name,
            'default': self.default,
            'ident': self.ident,
            'counts': {'total': self.total,
                       'read': 0,
                       'starred': 0,
                       'replied': 0},
            'mails': list(self.mails)
        }

    def as_json_string(self):
        tag_dict = self.as_dict()
        return json.dumps(tag_dict)

    def __repr__(self):
        return self.name
