#
# Copyright (c) 2015 ThoughtWorks, Inc.
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

from email.parser import Parser
import re
import logging

logger = logging.getLogger(__name__)


def _parse_charset_header(content_type_and_charset_header, default_charset='us-ascii'):
    try:
        return re.compile('.*charset="?([a-zA-Z0-9-]+)"?', re.MULTILINE | re.DOTALL).match(content_type_and_charset_header).group(1)
    except:
        return default_charset


class BodyParser(object):

    def __init__(self, content, content_type='text/plain; charset="us-ascii"', content_transfer_encoding=None):
        self._content = content
        self._content_type = content_type
        self._content_transfer_encoding = content_transfer_encoding

    def parsed_content(self):
        charset = _parse_charset_header(self._content_type)
        text = self._serialize_for_parser(charset)

        decoded_body = self._parse_and_decode(text)
        return unicode(decoded_body, charset, errors='replace')

    def _parse_and_decode(self, text):
        parsed_body = Parser().parsestr(text)
        decoded_body = self._unwrap_content_transfer_encoding(parsed_body)
        return decoded_body

    def _unwrap_content_transfer_encoding(self, parsed_body):
        return parsed_body.get_payload(decode=True)

    def _serialize_for_parser(self, charset):
        text = u'Content-Type: %s\n' % self._content_type
        if self._content_transfer_encoding is not None:
            text += u'Content-Transfer-Encoding: %s\n' % self._content_transfer_encoding

        text += u'\n'
        encoded_text = text.encode(charset)
        if isinstance(self._content, unicode):
            try:
                return encoded_text + self._content.encode(charset)
            except UnicodeError, e:
                logger.warn(
                    'Failed to encode content for charset %s. Ignoring invalid chars: %s' % (charset, e))
                return encoded_text + self._content.encode(charset, 'ignore')
        else:
            return encoded_text + self._content
