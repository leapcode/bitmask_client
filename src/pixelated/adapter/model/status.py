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


class Status:

    SEEN = u'\\Seen'
    ANSWERED = u'\\Answered'
    DELETED = u'\\Deleted'
    RECENT = u'\\Recent'

    FLAGS_TO_STATUSES = {
        SEEN: 'read',
        ANSWERED: 'replied',
        RECENT: 'recent'
    }

    @staticmethod
    def from_flag(flag):
        return Status.FLAGS_TO_STATUSES[flag]

    @staticmethod
    def from_flags(flags):
        return set(Status.from_flag(flag) for flag in flags if flag in Status.FLAGS_TO_STATUSES.keys())

    @staticmethod
    def to_flags(statuses):
        statuses_to_flags = dict(
            zip(Status.FLAGS_TO_STATUSES.values(), Status.FLAGS_TO_STATUSES.keys()))
        return [statuses_to_flags[status] for status in statuses]
