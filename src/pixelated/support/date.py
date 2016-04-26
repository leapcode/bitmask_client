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
import datetime

import dateutil.parser
from email.utils import formatdate
from dateutil.tz import tzlocal


def iso_now():
    return datetime.datetime.now(tzlocal()).isoformat()


def mail_date_now():
    date = dateutil.parser.parse(iso_now())
    return formatdate(float(date.strftime('%s')))
